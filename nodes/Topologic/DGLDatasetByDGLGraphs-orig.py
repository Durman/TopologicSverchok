import sys
sys.path.append(r"D:\Anaconda3\envs\py310\Lib\site-packages")
import bpy
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode

import numpy as np
import torch
import dgl
from dgl.data import DGLDataset

import topologic
from . import Replication

class GraphDGL(DGLDataset):
	def __init__(self, graphs, labels):
		super().__init__(name='GraphDGL')
		self.graphs = graphs
		self.labels = torch.LongTensor(labels)
		self.dim_nfeats = 1

	def __getitem__(self, i):
		return self.graphs[i], self.labels[i]

	def __len__(self):
		return len(self.graphs)

def processItem(item):
	dgl_graphs, dgl_labels = item
	if isinstance(dgl_graphs, list) == False:
		dgl_graphs = [dgl_graphs]
	if isinstance(dgl_labels, list) == False:
		dgl_labels = [dgl_labels]
	return GraphDGL(dgl_graphs, dgl_labels)

replication = [("Default", "Default", "", 1),("Trim", "Trim", "", 2),("Iterate", "Iterate", "", 3),("Repeat", "Repeat", "", 4),("Interlace", "Interlace", "", 5)]

class SvDGLDatasetByDGLGraphs(bpy.types.Node, SverchCustomTreeNode):
	"""
	Triggers: Topologic
	Tooltip: Creates a DGL Dataset by the input DGL Graphs and Labels
	"""
	bl_idname = 'SvDGLDatasetByDGLGraphs'
	bl_label = 'DGL.DatasetByDGLGraphs'
	Replication: EnumProperty(name="Replication", description="Replication", default="Default", items=replication, update=updateNode)
	Label: IntProperty(name='Label', default=0, update=updateNode)

	def sv_init(self, context):
		self.inputs.new('SvStringsSocket', 'DGL Graph')
		self.inputs.new('SvStringsSocket', 'Label').prop_name='Label'
		self.outputs.new('SvStringsSocket', 'DGL Dataset')

	def draw_buttons(self, context, layout):
		layout.prop(self, "Replication",text="")

	def process(self):
		if not any(socket.is_linked for socket in self.outputs):
			return
		if not any(socket.is_linked for socket in self.inputs):
			self.outputs['DGL Dataset'].sv_set([])
			return
		graphList = self.inputs['DGL Graph'].sv_get(deepcopy=True)
		labelList = self.inputs['Label'].sv_get(deepcopy=True)
		inputs = [[graphList], [labelList]]
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
		self.outputs['DGL Dataset'].sv_set(outputs)

def register():
	bpy.utils.register_class(SvDGLDatasetByDGLGraphs)

def unregister():
	bpy.utils.unregister_class(SvDGLDatasetByDGLGraphs)