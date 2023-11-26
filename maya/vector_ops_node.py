import sys
import math
from collections import namedtuple
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

maya_useNewAPI = True
SOLID_STYLE = omr.MUIDrawManager.kSolid
DASHED_STYLE = omr.MUIDrawManager.kDashed
DEFAULT_LINE_WIDTH = 1.0
COMPS_COLORS = (om.MColor((1.0, 0.0, 0.0)),
                om.MColor((0.0, 1.0, 0.0)),
                om.MColor((0.0, 0.0, 1.0)))
DEF_ARROW_HEIGHT = 0.3
DEF_ARROW_BASE = 0.4
VectorDrawData = namedtuple("VectorDrawData", ['points', 'color', 'line_style', 'line_width', 'show_coord'])


def _calc_arrow_head_points(camera_path, height=DEF_ARROW_HEIGHT, base=DEF_ARROW_BASE, dir_vector=None,
                            arrow_origin=None):
	"""
	Calculates arrow head points projected on a camera's plane of view.

	:param OpenMaya.MDagPath camera_path:
	:param float height:
	:param float base:
	:param OpenMaya.MVector dir_vector:
	:param OpenMaya.MPoint|OpenMaya.MVector arrow_origin:
	:return: list[OpenMaya.MPoint, OpenMaya.MPoint, OpenMaya.MPoint, OpenMaya.MPoint]
	"""
	camera_fn = om.MFnCamera(camera_path)
	cam_up_vector = camera_fn.upDirection(om.MSpace.kWorld)
	cam_view_vector = camera_fn.viewDirection(om.MSpace.kWorld)
	cam_base_vector = cam_up_vector ^ cam_view_vector
	if dir_vector:
		# Project the vector onto the camera's plane. Since both basis vectors of the camera's plane,
		# cam_up_vector and cam_view_vector, are orthonormal (both have length = 1.0 and are 90 degrees
		# apart), the projection calculation is simplified dot product between the direction vector and
		# each of the basis vectors. The projection vector will then be on the space of the camera's plane,
		# which is 2 dimensional. We'll associate the x, and y components with the cam_base_vector and
		# cam_up_vector, respectively. Therefore, the z component represents the plane's normal (cam_view_vector).
		dir_vector_in_cam_plane = ((dir_vector * cam_base_vector) * cam_base_vector) + (
					(dir_vector * cam_up_vector) * cam_up_vector)
	else:
		dir_vector_in_cam_plane = om.MVector(cam_up_vector)

	arrow_origin = om.MVector(arrow_origin) if arrow_origin else om.MVector()
	# Calculate the triangle points clock-wise starting from the top corner. By default, the triangle/arrow top
	# corner point will be the world's center, which leaves the other two below the grid and the resulting triangle
	# pointing towards the world's Y axis. It will have to be oriented based on the direction vector received as
	# argument.
	quats = cam_up_vector.rotateTo(dir_vector_in_cam_plane)
	or_cam_up_vector = cam_up_vector.rotateBy(quats)
	or_cam_base_vector = cam_base_vector.rotateBy(quats)
	triangle_points = [om.MPoint(om.MVector(0.0, 0.0, 0.0) + arrow_origin),
	                   om.MPoint((base * 0.5 * or_cam_base_vector) + (height * -1.0 * or_cam_up_vector) +
	                             arrow_origin),
	                   om.MPoint(
		                   (base * -0.5 * or_cam_base_vector) + (height * -1.0 * or_cam_up_vector) + arrow_origin),
	                   om.MPoint(om.MVector(0.0, 0.0, 0.0) + arrow_origin)]

	return triangle_points


class VectorsVis(omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/vectorsVis"
	drawRegistrantId = "VectorsVisPlugin"
	typeId = om.MTypeId(0x80007)

	line_width_attr = None
	in_vectors_data_attr = None
	end_attr = None
	color_attr = None
	coords_visible_attr = None
	line_style_attr = None
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
		mfn_num_attr.default = DEFAULT_LINE_WIDTH
		mfn_num_attr.affectsAppearance = True

		VectorsVis.end_attr = mfn_num_attr.createPoint("end", "endPoint")
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = True
		mfn_num_attr.affectsAppearance = True

		VectorsVis.color_attr = mfn_num_attr.createColor("color", "vectorColor")
		mfn_num_attr.writable = True
		mfn_num_attr.storable = True
		mfn_num_attr.keyable = False
		mfn_num_attr.affectsAppearance = True

		VectorsVis.line_style_attr = mfn_enum_attr.create("style", "lineStyle")
		mfn_enum_attr.addField("Solid", SOLID_STYLE)
		mfn_enum_attr.addField("Dashed", DASHED_STYLE)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = SOLID_STYLE
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.coords_visible_attr = mfn_enum_attr.create("coord", "showCoordinates")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 0
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.visible_attr = mfn_enum_attr.create("visible", "visible")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 1
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.in_vectors_data_attr = mfn_comp_attr.create("inVectors", "inVectors")
		mfn_comp_attr.addChild(VectorsVis.end_attr)
		mfn_comp_attr.addChild(VectorsVis.color_attr)
		mfn_comp_attr.addChild(VectorsVis.line_style_attr)
		mfn_comp_attr.addChild(VectorsVis.coords_visible_attr)
		mfn_comp_attr.addChild(VectorsVis.visible_attr)
		mfn_comp_attr.array = True
		mfn_comp_attr.storable = True
		mfn_comp_attr.writable = True
		mfn_comp_attr.affectsAppearance = True

		VectorsVis.addAttribute(VectorsVis.line_width_attr)
		VectorsVis.addAttribute(VectorsVis.in_vectors_data_attr)

	@classmethod
	def creator(cls):
		return cls()

	def compute(self, plug, data_block):
		data_block.setClean(plug)
		return

	def draw(self, view, path, style, status):
		pass


#######################################################################################################################
#
#  Viewport 2.0 override implementation
#
#######################################################################################################################

class VectorsDrawUserData(om.MUserData):
	_delete_after_user = True
	_camera_path = None
	_vectors_draw_data = None

	def __init__(self, camera_path):
		super(VectorsDrawUserData, self).__init__()
		self._camera_path = camera_path
		self._vectors_draw_data = []

	@property
	def vectors_arrow_height(self):
		return DEF_ARROW_HEIGHT

	@property
	def vectors_arrow_base(self):
		return DEF_ARROW_BASE

	def add_vector(self, end_point, origin_point=om.MPoint(0, 0, 0), color=om.MColor((1.0, 1.0, 1.0)),
	               line_style=SOLID_STYLE, line_width=DEFAULT_LINE_WIDTH, show_coord=False):
		"""
		Adds a vector draw data which includes its origin and end points, color, line style and width as well
		as whether its coordinates should be visible or not.

		:param OpenMaya.MPoint end_point:
		:param OpenMaya.MNPoint origin_point:
		:param OpenMaya.MColor color:
		:param int line_style:
		:param float line_width:
		:param bool show_coord:
		"""
		arrow_points = _calc_arrow_head_points(self._camera_path, self.vectors_arrow_height,
		                                       self.vectors_arrow_base, dir_vector=end_point - origin_point,
		                                       arrow_origin=end_point - origin_point)
		vector_points = [origin_point, end_point]
		for i, point in enumerate(arrow_points):
			if i > 1:
				vector_points.append(arrow_points[i - 1])
			vector_points.append(point)

		self._vectors_draw_data.append(VectorDrawData(vector_points, color, line_style, line_width, show_coord))

	def get_vectors_data(self):
		return self._vectors_draw_data

	def clear_draw_data(self):
		self._vectors_draw_data = []

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
		Called by Maya each time the object needs to be drawn. Any data needed from the Maya dependency graph must
		be retrieved and cached in this stage. It is invalid to pull data from the Maya dependency graph in the
		draw callback method and Maya may become unstable if that is attempted.

		Implementors may allow Maya to handle the data caching by returning a pointer to the data from this method.
		The pointer must be to a class derived from MUserData. This same pointer will be passed to the draw callback.
		On subsequent draws, the pointer will also be passed back into this method so that the data may be modified
		and reused instead of reallocated. If a different pointer is returned Maya will delete the old data. If the
		cache should not be maintained between draws, set the delete after use flag on the user data. In all cases,
		the lifetime and ownership of the user data is handled by Maya and the user should not try to delete the
		data themselves. Data caching occurs per-instance of the associated DAG object. The lifetime of the user
		data can be longer than the associated node, instance or draw override. Due to internal caching, the user
		data can be deleted after an arbitrary long time. One should therefore be careful to not access stale
		objects from the user data destructor. If it is not desirable to allow Maya to handle data caching, simply
		return NULL in this method and ignore the user data parameter in the draw callback method.

		:param OpenMaya.MDagPath obj_path:
		:param OpenMaya.MDagPath camera_path:
		:param OpenMayaRender.MFrameContext frame_context:
		:param OpenMaya.MUserData old_data:
		:return: The data to be passed to the draw callback method
		:rtype: VectorsDrawUserData
		"""

		mfn_dep_node = om.MFnDependencyNode(obj_path.node())
		in_vectors_plug = mfn_dep_node.findPlug(VectorsVis.in_vectors_data_attr, False)
		line_width = mfn_dep_node.findPlug("lineWidth", False).asDouble()
		start_point = om.MPoint(0.0, 0.0, 0.0)
		vectors_draw_data = VectorsDrawUserData(camera_path)

		for vector_id in range(in_vectors_plug.numElements()):
			vector_data_plug = in_vectors_plug.elementByLogicalIndex(vector_id)
			visible_plug = vector_data_plug.child(4)
			if not visible_plug.asBool():
				continue

			end_plug = vector_data_plug.child(0)
			color_plug = vector_data_plug.child(1)
			line_style = vector_data_plug.child(2).asShort()
			coord_vis = vector_data_plug.child(3).asBool()
			end_point = om.MPoint(end_plug.child(0).asDouble(),
			                      end_plug.child(1).asDouble(),
			                      end_plug.child(2).asDouble())
			color = om.MColor()
			color.r = color_plug.child(0).asFloat()
			color.g = color_plug.child(1).asFloat()
			color.b = color_plug.child(2).asFloat()

			vectors_draw_data.add_vector(end_point, origin_point=start_point, color=color,
			                             line_width=line_width, line_style=line_style,
			                             show_coord=coord_vis)

		return vectors_draw_data

	def addUIDrawables(self, obj_path, draw_manager, frame_context, data):
		"""
		Provides access to the MUIDrawManager, which can be used to queue up operations to draw simple UI shapes
		like lines, circles, text, etc.

		This method will only be called when hasUIDrawables() is overridden to return True. It is called after
		prepareForDraw() and carries the same restrictions on the sorts of operations it can perform.

		:param OpenMaya.MDagPath obj_path:
		:param OpenMayaRender.MUIDrawManager draw_manager:
		:param OpenMayaRender.MFrameContext frame_context:
		:param VectorsDrawUserData data:
		"""
		if data is None:
			return

		draw_manager.beginDrawable()
		draw_2d = False

		for vector_data in data.get_vectors_data():
			draw_manager.setLineWidth(vector_data.line_width)
			draw_manager.setLineStyle(vector_data.line_style)
			draw_manager.setColor(vector_data.color)
			draw_manager.lineList(om.MPointArray(vector_data.points), draw_2d)

			if vector_data.show_coord:
				end_point = vector_data.points[1]
				trunc_coord = [math.trunc(c * 100) / 100 for c in (end_point.x, end_point.y, end_point.z)]
				coord_text = "({}, {}, {})".format(*trunc_coord)
				draw_manager.text(end_point, coord_text, dynamic=True)

		draw_manager.endDrawable()
		return self


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
