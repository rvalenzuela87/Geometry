import sys
import ctypes
import math
from collections import namedtuple

import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

from Geometry.utils.Vector_Utils import vector_add, vector_sub


maya_useNewAPI = True


class VectorsVis(omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/vectorsVis"
	drawRegistrantId = "VectorsVisPlugin"
	typeId = om.MTypeId(0x80007)

	line_width_attr = None
	in_vectors_attr = None
	vectors_op_attr = None
	op_type_attr = None
	op_vectors_attr = None

	OP_TYPES = ("Add", "Subtract", "Scale")

	def __init_(self):
		super(VectorsVis, self).__init__()

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		mfn_enum_attr = om.MFnEnumAttribute()
		mfn_comp_attr = om.MFnCompoundAttribute()

		VectorsVis.line_width_attr = mfn_num_attr.create("width", "lineWidth", om.MFnNumericData.kDouble)
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.keyable = True
		mfn_num_attr.default = 2.0
		mfn_num_attr.affectsAppearance = True

		VectorsVis.in_vector_attr = mfn_num_attr.create("inVectors", "inVectors", om.MFnNumericData.k3Double)
		mfn_num_attr.array = True
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = True
		mfn_num_attr.affectsAppearance = True

		VectorsVis.op_type_attr = mfn_enum_attr.create("opType", "opType")
		for op_id, op_name in enumerate(VectorsVis.OP_TYPES):
			mfn_enum_attr.addField(op_name, op_id)

		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = True
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.op_vectors_attr = mfn_num_attr.create("opVectors", "opVectors", om.MFnNumericData.k3Double)
		mfn_num_attr.array = True
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = False
		mfn_num_attr.affectsAppearance = True

		VectorsVis.vectors_op_attr = mfn_comp_attr.create("ops", "vectorOps")
		mfn_comp_attr.addChild(VectorsVis.op_type_attr)
		mfn_comp_attr.addChild(VectorsVis.op_vectors_attr)
		mfn_comp_attr.array = True
		mfn_comp_attr.storable = True
		mfn_comp_attr.writable = True
		mfn_comp_attr.affectsAppearance = True

		VectorsVis.addAttribute(VectorsVis.line_width_attr)
		VectorsVis.addAttribute(VectorsVis.in_vector_attr)
		VectorsVis.addAttribute(VectorsVis.vectors_op_attr)

	@classmethod
	def creator(cls):
		return cls()

	def compute(self, plug, data_block):
		data_block.setClean(plug)

	def draw(self, view, path, style, status):
		pass


#######################################################################################################################
#
#  Viewport 2.0 override implementation
#
#######################################################################################################################

class VectorsDrawUserData(om.MUserData):
	_delete_after_user = True
	_vectors_points = None
	_line_width = 1.0

	def __init__(self):
		super(VectorsDrawUserData, self).__init__()
		self._vectors_points = []

	@property
	def vectors_points(self):
		return self._vectors_points

	@property
	def line_width(self):
		return self._line_width

	@line_width.setter
	def line_width(self, width):
		self._line_width = width

	def add_vector(self, start_point, end_point):
		self._vectors_points.append((start_point, end_point))

	def deleteAfterUser(self):
		return self._delete_after_user

	def setDeleteAfterUser(self, delete_after_use):
		"""

		:param bool delete_after_use:
		"""
		self._delete_after_user = delete_after_use


class VectorsVisDrawOverride(omr.MPxDrawOverride):
	_draw_apis = omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile | omr.MRenderer.kDirectX11
	_obj = None
	_line_width = 4.0

	def __init__(self, obj, callback=None, always_dirty=False):
		super(VectorsVisDrawOverride, self).__init__(obj, callback, always_dirty)

		self._obj = obj
		self._in_vectors = []

	@staticmethod
	def creator(obj, *args, **kwargs):
		print(">> Obj: {}".format(obj.apiTypeStr))
		return VectorsVisDrawOverride(obj)

	@property
	def line_width(self):
		return self._line_width

	def cleanUp(self):
		pass

	def supportedDrawAPIs(self):
		# Supports GL and DX
		return self._draw_apis

	def hasUIDrawables(self):
		return True

	def prepareForDraw(self, obj_path, camera_path, frame_context, old_data):
		"""

		:param OpenMaya.MDagPath obj_path:
		:param OpenMaya.MDagPath camera_path:
		:param OpenMayaRender.MFrameContext frame_context:
		:param OpenMaya.MUserData old_data:
		:return:
		:rtype: VectorsDrawUserData
		"""
		mfn_dep_node = om.MFnDependencyNode(self._obj)
		in_vectors_plug = mfn_dep_node.findPlug("inVectors", False)
		line_width_plug = mfn_dep_node.findPlug("lineWidth", False)
		vectors_draw_data = VectorsDrawUserData()

		for vector_id in range(in_vectors_plug.numElements()):
			vector_plug = in_vectors_plug.elementByLogicalIndex(vector_id)
			start_point = om.MPoint(0.0, 0.0, 0.0)
			end_point = om.MPoint(vector_plug.child(0).asDouble(),
			                      vector_plug.child(1).asDouble(),
			                      vector_plug.child(2).asDouble())

			vectors_draw_data.add_vector(start_point, end_point)

		vectors_draw_data.line_width = line_width_plug.asDouble()

		return vectors_draw_data

	def addUIDrawables(self, obj_path, draw_manager, frame_context, data):
		"""

		:param OpenMaya.MDagPath obj_path:
		:param OpenMayaRender.MUIDrawManager draw_manager:
		:param OpenMayaRender.MFrameContext frame_context:
		:param VectorsDrawUserData data:
		:return:
		"""

		for start_point, end_point in data.vectors_points:
			draw_manager.beginDrawable()
			draw_manager.setLineWidth(data.line_width)
			draw_manager.line(start_point, end_point)
			draw_manager.endDrawable()


def initializePlugin(obj):
	plugin = om.MFnPlugin(obj, "Rafael Valenzuela Ochoa", "1.0", "")

	try:
		plugin.registerNode(
			"vectorsVis",
			VectorsVis.typeId,
			VectorsVis.creator,
			VectorsVis.initialize,
			om.MPxNode.kLocatorNode,
			VectorsVis.drawDBClassification
		)
	except RuntimeError as re:
		sys.stderr.write("Failed to register node VectorsVis.")
		raise re

	# Register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.registerDrawOverrideCreator(
			VectorsVis.drawDBClassification,
			VectorsVis.drawRegistrantId,
			VectorsVisDrawOverride.creator
		)
	except:
		sys.stderr.write("Failed to register override for node SpaceVis")
		raise

	try:
		om.MSelectionMask.registerSelectionType("vectorsVisSelection")
		mel.eval("selectType -byName \"vectorsVisSelection\" 1")
	except:
		sys.stderr.write("Failed to register selection mask\n")
		raise


def uninitializePlugin(obj):
	plugin = om.MFnPlugin(obj)
	try:
		plugin.deregisterNode(VectorsVis.typeId)
	except RuntimeError as re:
		sys.stderr.write("Failed to de-register node VectorsVis")
		pass

	# De-register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.deregisterDrawOverrideCreator(
			VectorsVis.drawDBClassification,
			VectorsVis.drawRegistrantId
		)
	except:
		sys.stderr.write("Failed to de-register override for node VectorsVis")
		pass

	try:
		om.MSelectionMask.deregisterSelectionType("vectorsVisSelection")
	except:
		sys.stderr.write("Failed to de-register selection mask\n")
		pass
