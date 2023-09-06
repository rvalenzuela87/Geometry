import maya.cmds as cmds
import maya.OpenMaya as om
from Geometry.utils import Barycentric_Utils as bu


def selection_center(world=True):
	sel_objs_points = [bu.Point(*cmds.xform(obj, q=True, t=True, ws=world)) for obj in cmds.ls(sl=True, fl=True)]
	return bu.center_of_mass(sel_objs_points)


def soft_selection_center(world=True):
	"""

	:param bool world:
	:return:
	:rtype: list[float, float, float]
	"""
	space = om.MSpace.kWorld if world else om.MSpace.kObject
	symmetry = cmds.symmetricModelling(q=True, symmetry=True)
	sel_obj_points = []
	sel_list = om.MSelectionList()
	rich_sel_list = om.MRichSelection()

	om.MGlobal.getRichSelection(rich_sel_list)

	sides_count = 1 if not symmetry else 2
	for side in range(sides_count):
		sel_list.clear()
		if side:
			rich_sel_list.getSymmetry(sel_list)
		else:
			rich_sel_list.getSelection(sel_list)

		it_sel_list = om.MItSelectionList(sel_list)
		while not it_sel_list.isDone():
			shape_dag_path = om.MDagPath()
			component = om.MObject()

			it_sel_list.getDagPath(shape_dag_path, component)

			mesh_fn = om.MFnMesh(shape_dag_path)
			component_fn = om.MFnComponent(component)
			if not component_fn.hasWeights():
				continue

			single_indexed_comp_fn = om.MFnSingleIndexedComponent(component)

			for el_index in range(component_fn.elementCount()):
				comp_weight = component_fn.weight(el_index).influence()
				comp_id = single_indexed_comp_fn.element(el_index)
				comp_m_point = om.MPoint()

				mesh_fn.getPoint(comp_id, comp_m_point, space)

				comp_point = bu.WPoint(comp_m_point.x, comp_m_point.y, comp_m_point.z, comp_weight)
				sel_obj_points.append(comp_point)

			it_sel_list.next()

	return bu.center_of_mass(sel_obj_points)

