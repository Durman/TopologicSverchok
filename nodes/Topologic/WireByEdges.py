import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode

import topologic
from topologic import Vertex, Edge, Wire, Face, Shell, Cell, CellComplex, Cluster, Topology, Dictionary

# From https://stackabuse.com/python-how-to-flatten-list-of-lists/
def flatten(element):
	returnList = []
	if isinstance(element, list) == True:
		for anItem in element:
			returnList = returnList + flatten(anItem)
	else:
		returnList = [element]
	return returnList

def list_level_iter(lst, level, _current_level: int= 1):
    """
    Iterate over all lists with given nesting
    With level 1 it will return the given list
    With level 2 it will iterate over all nested lists in the main one
    If a level does not have lists on that level it will return empty list
    _current_level - for internal use only
    """
    if _current_level < level:
        try:
            for nested_lst in lst:
                if not isinstance(nested_lst, list):
                    raise TypeError
                yield from list_level_iter(nested_lst, level, _current_level + 1)
        except TypeError:
            yield []
    else:
        yield lst

def processItem(item):
	wire = None
	for anEdge in item:
		if anEdge.Type() == 2:
			if wire == None:
				wire = anEdge
			else:
				try:
					wire = wire.Merge(anEdge)
				except:
					continue
	if wire.Type() != 4:
		raise Exception("Error: Could not create Wire. Please check input")
	return wire

def recur(input):
	output = []
	if input == None:
		return []
	if isinstance(input[0], list):
		for anItem in input:
			output.append(recur(anItem))
	else:
		output = processItem(input)
	return output

class SvWireByEdges(bpy.types.Node, SverchCustomTreeNode):
	"""
	Triggers: Topologic
	Tooltip: Creates a Wire from the list of input Edges    
	"""
	bl_idname = 'SvWireByEdges'
	bl_label = 'Wire.ByEdges'
	Level: IntProperty(name='Level', default =2,min=1, update = updateNode)

	def sv_init(self, context):
		self.inputs.new('SvStringsSocket', 'Edges')
		self.inputs.new('SvStringsSocket', 'Level').prop_name='Level'
		self.outputs.new('SvStringsSocket', 'Wire')

	def process(self):
		if not any(socket.is_linked for socket in self.outputs):
			return
		edgeList = self.inputs['Edges'].sv_get(deepcopy=False)
		level = flatten(self.inputs['Level'].sv_get(deepcopy=False, default= 2))
		if isinstance(level,list):
			level = int(level[0])
		edgeList = list(list_level_iter(edgeList,level))
		edgeList = [flatten(t) for t in edgeList]
		outputs = []
		for t in range(len(edgeList)):
			outputs.append(processItem(edgeList[t]))
		self.outputs['Wire'].sv_set(outputs)

def register():
    bpy.utils.register_class(SvWireByEdges)

def unregister():
    bpy.utils.unregister_class(SvWireByEdges)
