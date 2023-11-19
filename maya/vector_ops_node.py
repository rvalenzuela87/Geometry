import sys
import ctypes
import math
from collections import namedtuple

import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

from Geometry.utils.Vector_Utils import vector_projection_on_plane


maya_useNewAPI = True


class VectorsVisMixIn(object):
	SOLID_STYLE = omr.MUIDrawManager.kSolid
	DASHED_STYLE = omr.MUIDrawManager.kDashed
	DEFAULT_LINE_WIDTH = 1.0

	OP_TYPES = ("Add", "Subtract", "Scale")
	COMPS_COLORS = (om.MColor((1.0, 0.0, 0.0)),
	                om.MColor((0.0, 1.0, 0.0)),
	                om.MColor((0.0, 0.0, 1.0)))

	def __init__(self, *args, **kwargs):
		super(VectorsVisMixIn, self).__init__(*args, **kwargs)
		self._line_width = self.DEFAULT_LINE_WIDTH

	@property
	def line_width(self):
		return self._line_width

	@staticmethod
	def _calc_arrow_head_points(camera_path, arrow_origin_point=None):
		"""
		Calculates arrow head points projected on a camera's plane of view.

		:param OpenMaya.MDagPath camera_path:
		:param OpenMaya.MPoint arrow_origin_point:
		:return: tuple(OpenMaya.MPoint, OpenMaya.MPoint, OpenMaya.MPoint)
		"""
		camera_fn = om.MFnCamera(camera_path)
		cam_up_dir_vector = camera_fn.upDirection(om.MSpace.kWorld)
		cam_view_dir_vector = camera_fn.viewDirection(om.MSpace.kWorld)
		cam_base_vector = cam_up_dir_vector ^ cam_view_dir_vector
		origin_vector = om.MVector(arrow_origin_point) if arrow_origin_point else om.MVector()

		if arrow_origin_point:
			# Project the vector to the camera's plane. Since both basis vectors (cam_up_dir_vector and
			# cam_view_dir_vector) are orthonormal (both have length = 1.0 and are 90 degrees apart),
			# the projection calculation is simplified (dot product).
			base_coord = origin_vector * cam_base_vector
			up_coord = origin_vector * cam_up_dir_vector

			# The projection vector is now on the space of the camera's plane, which is 2 dimensional. We'll
			# associate the x, and y components with the cam_base_vector and cam_up_dir_vector, respectively.
			# Therefore, the z component represents the plane's normal (cam_view_dir_vector).
			proj_vector = om.MVector(base_coord, up_coord, 0.0)
		else:
			proj_vector = om.MVector(1.0, 1.0, 0.0)

		# Normalize it and inverse it.
		proj_vector.normalize()
		proj_vector *= -1.0

		# Make a copy of the projection vector and rotate it by 30 deg in the plane's normal (z axis).
		first_arrow_side_vector = proj_vector.rotateBy(om.MVector.kZaxis, math.radians(30.0))

		# Make a copy and rotate it by -30 deg in the plane's normal (camera view direction vector).
		second_arrow_side_vector = proj_vector.rotateBy(om.MVector.kZaxis, math.radians(-30.0))

		# Convert the first and second rotated vectors to 3D space, by multiplying its x and y components
		# times the cam_base_vector and cam_up_dir_vector, respectively and then adding them.
		first_3d_vector = (first_arrow_side_vector.x * cam_base_vector) + (first_arrow_side_vector.y * cam_up_dir_vector)
		second_3d_vector = (second_arrow_side_vector.x * cam_base_vector) + (second_arrow_side_vector.y * cam_up_dir_vector)

		first_3d_vector += origin_vector
		second_3d_vector += origin_vector

		first_arrow_point = om.MPoint(first_3d_vector.x, first_3d_vector.y, first_3d_vector.z)
		second_arrow_point = om.MPoint(second_3d_vector.x, second_3d_vector.y, second_3d_vector.z)

		return arrow_origin_point, first_arrow_point, second_arrow_point

	@classmethod
	def convert_to_arrow_points(cls, start_point, end_point, camera_path):
		"""
		Adds a triangle, on the camera's plane and at the end of the line represented by the start and end points
		received as argument.

		:param OpenMaya.MPoint start_point:
		:param OpenMaya.MPoint end_point:
		:param OpenMaya.MDagPath camera_path:
		:return:
		:rtype: tuple(MPoint, MPoint, MPoint, MPoint, MPoint)
		"""
		arrow_origin_vector = end_point - start_point
		arrow_origin_point = om.MPoint(arrow_origin_vector.x, arrow_origin_vector.y, arrow_origin_vector.z)
		__, first_tri_point, second_tri_point = cls._calc_arrow_head_points(camera_path,
		                                                                    arrow_origin_point=arrow_origin_point)

		# Make a list with the start point, end point, (first rotated vector + end point),
		# (second rotated vector + end point), end point.
		return (start_point,
		        end_point,
		        end_point,
		        first_tri_point,
		        first_tri_point,
		        second_tri_point,
		        second_tri_point,
		        end_point)


class VectorsVis(VectorsVisMixIn, omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/vectorsVis"
	drawRegistrantId = "VectorsVisPlugin"
	typeId = om.MTypeId(0x80007)

	line_width_attr = None
	in_vectors_data_attr = None
	origin_attr = None
	end_attr = None
	color_attr = None
	visible_attr = None

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
		mfn_num_attr.keyable = False
		mfn_num_attr.default = VectorsVis.DEFAULT_LINE_WIDTH
		mfn_num_attr.affectsAppearance = True

		VectorsVis.origin_attr = mfn_num_attr.createPoint("origin", "origin")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False

		VectorsVis.end_attr = mfn_num_attr.createPoint("end", "endPoint")
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = True
		mfn_num_attr.affectsAppearance = True

		VectorsVis.color_attr = mfn_num_attr.createColor("color", "vectorColor")
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = False

		VectorsVis.visible_attr = mfn_enum_attr.create("visible", "visible")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.in_vectors_data_attr = mfn_comp_attr.create("inVectors", "inVectors")
		mfn_comp_attr.addChild(VectorsVis.origin_attr)
		mfn_comp_attr.addChild(VectorsVis.end_attr)
		mfn_comp_attr.addChild(VectorsVis.color_attr)
		mfn_comp_attr.addChild(VectorsVis.visible_attr)
		mfn_comp_attr.array = True
		mfn_comp_attr.storable = True
		mfn_comp_attr.writable = True
		mfn_comp_attr.affectsAppearance = True

		VectorsVis.op_type_attr = mfn_enum_attr.create("opType", "opType")
		for op_id, op_name in enumerate(VectorsVis.OP_TYPES):
			mfn_enum_attr.addField(op_name, op_id)

		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = True
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.op_vectors_attr = mfn_num_attr.createPoint("points", "points")
		mfn_num_attr.array = True
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = False
		mfn_num_attr.affectsAppearance = True

		VectorsVis.addAttribute(VectorsVis.line_width_attr)
		VectorsVis.addAttribute(VectorsVis.in_vectors_data_attr)

	@classmethod
	def creator(cls):
		return cls()

	def compute(self, plug, data_block):
		print(">> Plug to compute: {}".format(plug.name()))
		plug_attribute = plug.attribute() if not plug.isChild else plug.parent().attribute()
		if not plug_attribute == self.origin_attr:
			print(">> Attribute not supported")
			data_block.setClean(plug)
			return

		data_block.setClean(plug)
		return

		if plug.isElement:
			out_log_index = plug.logicalIndex()
		elif plug.isChild:
			out_log_index = plug.parent().logicalIndex()
		else:
			print(">> Ignoring plug")
			data_block.setClean(plug)
			return

		vectors_op_array_data_handle = data_block.inputArrayValue(self.vectors_op_attr)
		vectors_op_array_data_handle.jumpToLogicalElement(out_log_index)
		op_data_handle = vectors_op_array_data_handle.inputValue()
		op_type = op_data_handle.child(self.op_type_attr).asInt()
		if op_type == 2:
			print(">> Vector scale operation not supported, yet.")
			data_block.setClean(plug)
			return

		op_vectors_array_data_handle = om.MArrayDataHandle(op_data_handle.child(self.op_vectors_attr))
		result_vector = None

		while not op_vectors_array_data_handle.isDone():
			op_vector = om.MVector(*op_vectors_array_data_handle.inputValue().asFloat3())
			print(">> >> {}".format(op_vector))
			if result_vector is None:
				result_vector = op_vector
			elif op_type == 0:
				result_vector += op_vector
			else:
				result_vector -= op_vector

			op_vectors_array_data_handle.next()

		print(">> Result: {}".format(result_vector))
		data_block.outputValue(plug).set3Float(result_vector.x, result_vector.y, result_vector.z)
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
	_vectors_colors = None
	_line_width = 1.0

	def __init__(self):
		super(VectorsDrawUserData, self).__init__()
		self._vectors_points = []
		self._vectors_colors = []

	@property
	def vectors_points(self):
		return self._vectors_points

	@vectors_points.setter
	def vectors_points(self, points):
		if type(points) not in (list, tuple, iter):
			raise TypeError()

		self._vectors_points = points

	@property
	def vectors_colors(self):
		return self._vectors_colors

	@vectors_colors.setter
	def vectors_colors(self, colors):
		if type(colors) not in (list, tuple, iter):
			raise TypeError()

		self._vectors_colors = colors

	@property
	def line_width(self):
		return self._line_width

	@line_width.setter
	def line_width(self, width):
		self._line_width = width

	def deleteAfterUser(self):
		return self._delete_after_user

	def setDeleteAfterUser(self, delete_after_use):
		"""

		:param bool delete_after_use:
		"""
		self._delete_after_user = delete_after_use


class VectorsVisDrawOverride(VectorsVisMixIn, omr.MPxDrawOverride):
	_draw_apis = omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile | omr.MRenderer.kDirectX11
	_obj = None
	_line_width = 4.0

	def __init__(self, obj, callback=None, always_dirty=True):
		"""

		:param OpenMaya.MObject obj:
		:param GeometryOverrideCb callback:
		:param bool always_dirty: If true, the object will re-draw on DG dirty propagation and whenever the
			viewing camera moves. If false, it will only re-draw on dirty propagation.
		"""
		super(VectorsVisDrawOverride, self).__init__(obj, callback, always_dirty)

		self._obj = obj
		self._in_vectors = []

	@staticmethod
	def creator(obj, *args, **kwargs):
		return VectorsVisDrawOverride(obj)

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

		mfn_dep_node = om.MFnDependencyNode(obj_path.node())
		in_vectors_plug = mfn_dep_node.findPlug(VectorsVis.in_vectors_data_attr, False)
		line_width_plug = mfn_dep_node.findPlug("lineWidth", False)
		vectors_points = []
		vectors_colors = []
		start_point = om.MPoint(0.0, 0.0, 0.0)

		for vector_id in range(in_vectors_plug.numElements()):
			vector_data_plug = in_vectors_plug.elementByLogicalIndex(vector_id)
			end_plug = vector_data_plug.child(1)
			end_point = om.MPoint(end_plug.child(0).asDouble(),
			                      end_plug.child(1).asDouble(),
			                      end_plug.child(2).asDouble())
			color_plug = vector_data_plug.child(2)
			color = om.MColor()
			color.r = color_plug.child(0).asFloat()
			color.g = color_plug.child(1).asFloat()
			color.b = color_plug.child(2).asFloat()
			vectors_colors.append(color)
			vectors_points.append(self.convert_to_arrow_points(start_point, end_point, camera_path))

		# Calculate origin arrow's points
		parent_transform_dag_path = om.MDagPath(obj_path).pop()
		world_transform_matrix = om.MTransformationMatrix(parent_transform_dag_path.inclusiveMatrix())
		world_translation = world_transform_matrix.translation(om.MSpace.kWorld)

		origin_vector = self.convert_to_arrow_points((world_translation * -1), start_point, camera_path)
		origin_color = om.MColor([1.0, 1.0, 1.0])

		vectors_points.append(origin_vector)
		vectors_colors.append(origin_color)

		vectors_draw_data = VectorsDrawUserData()
		vectors_draw_data.line_width = line_width_plug.asDouble()
		vectors_draw_data.vectors_points = vectors_points
		vectors_draw_data.vectors_colors = vectors_colors

		return vectors_draw_data

	def addUIDrawables(self, obj_path, draw_manager, frame_context, data):
		"""

		:param OpenMaya.MDagPath obj_path:
		:param OpenMayaRender.MUIDrawManager draw_manager:
		:param OpenMayaRender.MFrameContext frame_context:
		:param VectorsDrawUserData data:
		:return:
		"""
		if data is None:
			return

		draw_manager.beginDrawable()
		draw_manager.setLineWidth(data.line_width)
		draw_2d = False

		for points, color in zip(data.vectors_points, data.vectors_colors):
			draw_manager.setLineStyle(self.SOLID_STYLE)
			draw_manager.setColor(color)
			draw_manager.lineList(om.MPointArray(points), draw_2d)

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
