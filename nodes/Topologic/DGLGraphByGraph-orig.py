#import sys
#sys.path.append(r"D:\Anaconda3\envs\py310\Lib\site-packages")
import bpy
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode

import dgl
from dgl.data import DGLDataset
import torch
import numpy as np

import topologic
from . import Replication, DictionaryValueAtKey

def vertexIndex(v, vertexList, tolerance):
	for i in range(len(vertexList)):
		d = topologic.VertexUtility.Distance(v, vertexList[i])
		if d < tolerance:
			return i
	return None

def graphVertices(graph):
	vertices = []
	if graph:
		try:
			_ = graph.Vertices(vertices)
		except:
			print("ERROR: (Topologic>Graph.Vertices) operation failed.")
			vertices = None
	if vertices:
		return vertices
	else:
		return []

def graphEdges(graph):
	if graph:
		try:
			vertices = []
			edges = []
			_ = graph.Vertices(vertices)
			_ = graph.Edges(vertices, 0.001, edges)
		except:
			print("ERROR: (Topologic>Graph.Edges) operation failed.")
			edges = None
	if edges:
		return edges
	else:
		return []

def adjacentVertices(graph, vertex):
	vertices = []
	_ = graph.AdjacentVertices(vertex, vertices)
	return list(vertices)

def oneHotEncode(inputList, categories):
	returnList = []
	for anItem in inputList:
		row = []
		for i in range(len(categories)):
			if anItem == categories[i]:
				row.append(1)
			else:
				row.append(0)
		returnList.append(row)
	return returnList

def processItem(item):
	graph, bidirectional, key, categories, tolerance = item
	graph_dict = {}
	vertices = graphVertices(graph)
	edges = graphEdges(graph)
	graph_dict["num_nodes"] = len(vertices)
	graph_dict["src"] = []
	graph_dict["dst"] = []
	graph_dict["node_labels"] = {}
	nodes = []
	graph_edges = []

	# This is a hack, please replace
	test_list = []
	for i in range(len(vertices)):
		vDict = vertices[i].GetDictionary()
		vLabel = DictionaryValueAtKey.processItem([vDict, key])
		graph_dict["node_labels"][i] = vLabel
		nodes.append(i)
		# This is a hack, please replace
		test_list.append(vLabel)

	# Here we need to call oneHotEncode to create the one host encoding.
	# What is the input list we need here?
	# This is a hack, please replace.
	one_hot_encoded_list = oneHotEncode(test_list, categories)
	print("Categories", categories)
	print("Test List", test_list)
	print("One-Hot-Encoded List",one_hot_encoded_list)
	# Do something with the one_hot_encoded list

	for i in range(len(edges)):
		e = edges[i]
		sv = e.StartVertex()
		ev = e.EndVertex()
		sn = nodes[vertexIndex(sv, vertices, tolerance)]
		en = nodes[vertexIndex(ev, vertices, tolerance)]
		if (([sn,en] in graph_edges) == False) and (([en,sn] in graph_edges) == False):
			graph_edges.append([sn,en])

	for anEdge in graph_edges:
		graph_dict["src"].append(anEdge[0])
		graph_dict["dst"].append(anEdge[1])

	# Create DDGL graph
	src = np.array(graph_dict["src"])
	dst = np.array(graph_dict["dst"])
	num_nodes = graph_dict["num_nodes"]
	# Create a graph
	dgl_graph = dgl.graph((src, dst), num_nodes=num_nodes)
	dgl_graph.ndata['attr'] = torch.ones(num_nodes, 1)
	if bidirectional:
		dgl_graph = dgl.add_reverse_edges(dgl_graph)
	return dgl_graph

replication = [("Default", "Default", "", 1),("Trim", "Trim", "", 2),("Iterate", "Iterate", "", 3),("Repeat", "Repeat", "", 4),("Interlace", "Interlace", "", 5)]

class SvDGLGraphByGraph(bpy.types.Node, SverchCustomTreeNode):
	"""
	Triggers: Topologic
	Tooltip: Creates a DGL Graph from the input Topologic Graph
	"""
	bl_idname = 'SvDGLGraphByGraph'
	bl_label = 'DGL.DGLGraphByGraph'
	Replication: EnumProperty(name="Replication", description="Replication", default="Default", items=replication, update=updateNode)
	Key: StringProperty(name='Vertex Label Key', default="ID", update=updateNode)
	Bidirectional: BoolProperty(name="Bidirectional", default=True, update=updateNode)
	ToleranceProp: FloatProperty(name="Tolerance", default=0.0001, min=0, precision=4, update=updateNode)

	def sv_init(self, context):
		self.inputs.new('SvStringsSocket', 'Graph')
		self.inputs.new('SvStringsSocket', 'Bidirectional').prop_name = 'Bidirectional'
		self.inputs.new('SvStringsSocket', 'Vertex Label Key').prop_name='Key'
		self.inputs.new('SvStringsSocket', 'Vertex Categories')
		self.inputs.new('SvStringsSocket', 'Tolerance').prop_name = 'ToleranceProp'
		self.outputs.new('SvStringsSocket', 'DGL Graph')

	def draw_buttons(self, context, layout):
		layout.prop(self, "Replication",text="")

	def process(self):
		if not any(socket.is_linked for socket in self.outputs):
			return
		if not any(socket.is_linked for socket in self.inputs):
			self.outputs['DGL Graph'].sv_set([])
			return
		graphList = self.inputs['Graph'].sv_get(deepcopy=True)
		bidirectionalList = self.inputs['Bidirectional'].sv_get(deepcopy=True)
		keyList = self.inputs['Vertex Label Key'].sv_get(deepcopy=True)
		categoriesList = self.inputs['Vertex Categories'].sv_get(deepcopy=True)
		toleranceList = self.inputs['Tolerance'].sv_get(deepcopy=True)
		graphList = Replication.flatten(graphList)
		bidirectionalList = Replication.flatten(bidirectionalList)
		keyList = Replication.flatten(keyList)
		toleranceList = Replication.flatten(toleranceList)
		inputs = [graphList, bidirectionalList, keyList, categoriesList, toleranceList]
		if ((self.Replication) == "Default"):
			inputs = Replication.iterate(inputs)
			inputs = Replication.transposeList(inputs)
		if ((self.Replication) == "Trim"):
			inputs = Replication.trim(inputs)
			inputs = Replication.transposeList(inputs)
		elif ((self.Replication) == "Iterate"):
			inputs = Replication.iterate(inputs)
			inputs = Replication.transposeList(inputs)
		elif ((self.Replication) == "Repeat"):
			inputs = Replication.repeat(inputs)
			inputs = Replication.transposeList(inputs)
		elif ((self.Replication) == "Interlace"):
			inputs = list(Replication.interlace(inputs))
		outputs = []
		for anInput in inputs:
			outputs.append(processItem(anInput))
		self.outputs['DGL Graph'].sv_set(outputs)

def register():
	bpy.utils.register_class(SvDGLGraphByGraph)

def unregister():
	bpy.utils.unregister_class(SvDGLGraphByGraph)