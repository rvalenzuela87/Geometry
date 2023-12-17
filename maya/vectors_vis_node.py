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
DEF_ARROW_HEIGHT = 0.4
DEF_ARROW_BASE = 0.3
VectorDrawData = namedtuple("VectorDrawData", ['label', 'points', 'color', 'line_style', 'line_width', 'show_coord'])
DEFAULT_VECTOR_LABEL = "v"
DEF_DETAIL_FONT_SIZE = omr.MUIDrawManager.kDefaultFontSize


def _coordinates_to_text(point):
	"""

	:param OpenMaya.MPoint|OpenMaya.MVector point:
	:return: Point's coordinates in the format "(x.xxx, x.xxx, x.xxx)".
	:rtype: str
	"""
	trunc_coord = [math.trunc(c * 100) / 100 for c in (point.x, point.y, point.z)]
	return "({}, {}, {})".format(*trunc_coord)


def _build_vector_vis_draw_data(end_point, camera_path, label=DEFAULT_VECTOR_LABEL, arrow_head_scale=1.0,
                                parent_matrix=None, color=None, line_style=SOLID_STYLE, line_width=DEFAULT_LINE_WIDTH,
                                show_coords=False):
	"""
	Builds a vector visualisation data (VectorDrawData) from an end point.

	:param OpenMaya.MPoint end_point:
	:param OpenMaya.MDagPath camera_path:
	:param str label:
	:param float arrow_head_scale:
	:param OpenMaya.MMatrix|None parent_matrix: World space matrix
	:param OpenMaya.MColor|None color:
	:param int line_style:
	:param float line_width:
	:param bool show_coords:
	:return: Vector visualisation data (VectorDrawData)
	:rtype: VectorDrawData
	"""
	camera_fn = om.MFnCamera(camera_path)
	cam_up_vector = camera_fn.upDirection(om.MSpace.kWorld)
	cam_view_vector = camera_fn.viewDirection(om.MSpace.kWorld)
	cam_base_vector = cam_up_vector ^ cam_view_vector
	start_point = om.MPoint(0.0, 0.0, 0.0)
	if parent_matrix:
		w_position = om.MTransformationMatrix(parent_matrix).translation(om.MSpace.kWorld)
		arrow_origin = (om.MVector(end_point) * parent_matrix) + w_position
		dir_vector = (end_point - start_point) * parent_matrix
		parent_inv_matrix = parent_matrix.inverse()
	else:
		arrow_origin = om.MVector(end_point)
		dir_vector = end_point - start_point
		parent_inv_matrix = None

	# Project the direction vector onto the camera's plane. Since both basis vectors of the camera's plane,
	# cam_up_vector and cam_view_vector, are orthonormal (both have length = 1.0 and are 90 degrees
	# apart), the projection calculation is the simplified dot product between the direction vector and
	# each of the planes' base vectors. This will result in the projected vector's coordinates in the camera's
	# plane's space.
	cam_base_vector_scale = dir_vector * cam_base_vector
	cam_up_vector_scale = dir_vector * cam_up_vector

	# Once the projected coordinates in the plane's space are calculated, we use them to scale the plane's
	# base vectors which will result in the projected vector's world space coordinates.
	dir_vector_cam_plane_proy = (cam_base_vector_scale * cam_base_vector) + (cam_up_vector_scale * cam_up_vector)

	# Calculate the triangle points clock-wise starting from the top corner. By default, the triangle/arrow top
	# corner point will be the world's center, which leaves the other two below the grid and the resulting triangle
	# pointing towards the world's Y axis. It will have to be oriented based on the direction vector received as
	# argument.
	quats = cam_up_vector.rotateTo(dir_vector_cam_plane_proy)
	or_cam_up_vector = cam_up_vector.rotateBy(quats)
	or_cam_base_vector = cam_base_vector.rotateBy(quats)
	arrow_local_coord = [
		(0, 0),
		(DEF_ARROW_BASE * 0.5 * arrow_head_scale, DEF_ARROW_HEIGHT * -1.0 * arrow_head_scale),
		(DEF_ARROW_BASE * -0.5 * arrow_head_scale, DEF_ARROW_HEIGHT * -1.0 * arrow_head_scale),
		(0, 0)
	]

	draw_points = [start_point, end_point]
	for i, local_coord in enumerate(arrow_local_coord):
		if i > 1:
			draw_points.append(om.MPoint(draw_points[-1]))

		base_vector_scale, up_vector_scale = local_coord
		scaled_up_vector = up_vector_scale * or_cam_up_vector
		scaled_base_vector = base_vector_scale * or_cam_base_vector
		arrow_point = om.MPoint(scaled_up_vector + scaled_base_vector + arrow_origin)

		# Transform the arrow points from world space coordinates to the matrix
		if parent_inv_matrix:
			arrow_point *= parent_inv_matrix

		draw_points.append(arrow_point)

	return VectorDrawData(label, draw_points, color, line_style, line_width, show_coords)


class VectorsVisMixIn(object):
	basis_vectors = [om.MVector(1.0, 0.0, 0.0),
	                 om.MVector(0.0, 1.0, 0.0),
	                 om.MVector(0.0, 0.0, 1.0)]
	basis_labels = ['x', 'y', 'z']

	def __init__(self, *args, **kwargs):
		super(VectorsVisMixIn, self).__init__(*args, **kwargs)

	@staticmethod
	def get_vectors_data(vector_vis_shape_path):
		"""

		:param OpenMaya.MDagPath vector_vis_shape_path: Path to vectorsVis node
		:return:
		:rtype: iter(tuple(str, OpenMaya.MPoint, OpenMaya.MColor, int, bool),)
		"""
		mfn_dep_node = om.MFnDependencyNode(vector_vis_shape_path.node())
		in_vectors_plug = mfn_dep_node.findPlug(VectorsVis.in_vectors_data_attr, False)

		for vector_id in range(in_vectors_plug.numElements()):
			vector_data_plug = in_vectors_plug.elementByLogicalIndex(vector_id)
			visible_plug = vector_data_plug.child(VectorsVis.visible_attr)
			if not visible_plug.asBool():
				continue

			label = vector_data_plug.child(VectorsVis.label_attr).asString()
			end_plug = vector_data_plug.child(VectorsVis.end_attr)
			color_plug = vector_data_plug.child(VectorsVis.color_attr)
			line_style = vector_data_plug.child(VectorsVis.line_style_attr).asShort()
			coord_vis = vector_data_plug.child(VectorsVis.show_coord_attr).asBool()
			end_point = om.MPoint(end_plug.child(0).asDouble(),
			                      end_plug.child(1).asDouble(),
			                      end_plug.child(2).asDouble())
			color = om.MColor()
			color.r = color_plug.child(0).asFloat()
			color.g = color_plug.child(1).asFloat()
			color.b = color_plug.child(2).asFloat()

			yield label, end_point, color, line_style, coord_vis

	@classmethod
	def get_vectors_draw_data_from_shape(cls, vector_vis_shape_path, camera_path):
		"""

		:param OpenMaya.MDagPath vector_vis_shape_path: Path to vectorsVis node
		:param OpenMaya.MDagPath camera_path: Path to current camera
		:return:
		:rtype: iter(VectorDrawData)
		"""
		w_trans_matrix = vector_vis_shape_path.exclusiveMatrix()
		mfn_dep_node = om.MFnDependencyNode(vector_vis_shape_path.node())
		line_width = mfn_dep_node.findPlug(VectorsVis.line_width_attr, False).asDouble()
		arrow_head_scale = mfn_dep_node.findPlug(VectorsVis.arrow_head_size_attr, False).asDouble()

		for label, end_point, color, line_style, coord_vis in cls.get_vectors_data(vector_vis_shape_path):
			yield _build_vector_vis_draw_data(end_point, camera_path, label=label, arrow_head_scale=arrow_head_scale,
			                                  parent_matrix=w_trans_matrix, color=color, line_style=line_style,
			                                  line_width=line_width, show_coords=coord_vis)

	@classmethod
	def get_base_vectors_from_shape(cls, vector_vis_shape_path, camera_path):
		"""

		:param OpenMaya.MDagPath vector_vis_shape_path: Path to vectorsVis node
		:param OpenMaya.MDagPath camera_path: Path to current camera
		:return:
		:rtype: iter(VectorDrawData)
		"""
		w_trans_matrix = vector_vis_shape_path.exclusiveMatrix()
		mfn_dep_node = om.MFnDependencyNode(vector_vis_shape_path.node())
		arrow_head_scale = mfn_dep_node.findPlug(VectorsVis.arrow_head_size_attr, False).asDouble()

		for base_vector, color, label in zip(cls.basis_vectors, COMPS_COLORS, cls.basis_labels):
			base_point = om.MPoint(base_vector)
			yield _build_vector_vis_draw_data(base_point, camera_path, label=label, arrow_head_scale=arrow_head_scale,
			                                  parent_matrix=w_trans_matrix, color=color, line_style=SOLID_STYLE,
			                                  line_width=DEFAULT_LINE_WIDTH, show_coords=True)

	@staticmethod
	def build_vector_detail(label, end_point):
		"""

		:param str label:
		:param OpenMaya.MPoint end_point:
		:return:
		"rtype: str
		"""
		length = om.MVector(end_point).length()
		detail = "{} = {}, |{}| = {}".format(label, _coordinates_to_text(end_point), label, length)
		return detail


class VectorsVis(VectorsVisMixIn, omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/vectorsVis"
	drawRegistrantId = "VectorsVisPlugin"
	typeId = om.MTypeId(0x80007)

	line_width_attr = None
	in_vectors_data_attr = None
	end_attr = None
	color_attr = None
	label_attr = None
	show_coord_attr = None
	show_length_attr = None
	show_label_attr = None
	show_detailed_attr = None
	arrow_head_size_attr = None
	details_font_size_attr = None
	line_style_attr = None
	visible_attr = None
	basis_visible_attr = None
	base1_attr = None
	base2_attr = None
	base3_attr = None
	upd_parent_matrix_attr = None

	kDefaultVectorLabel = "v"

	def __init_(self):
		super(VectorsVis, self).__init__()

	@staticmethod
	def _draw_from_vector_draw_data(draw_data, view, gl_ft, text=None):
		"""

		:param VectorDrawData draw_data:
		:param OpenMayaUI.M3dView view:
		:param gl_ft:
		:param str text:
		"""
		# Start drawing the vectors' lines
		color = draw_data.color
		gl_ft.glColor4f(color.r, color.g, color.b, 1.0)
		gl_ft.glLineWidth(draw_data.line_width)

		import maya.OpenMayaRender as v1omr

		# Start drawing the vector's lines
		gl_ft.glBegin(v1omr.MGL_LINES)

		for i in range(0, len(draw_data.points), 2):
			start_point = draw_data.points[i]
			end_point = draw_data.points[i + 1]
			gl_ft.glVertex3f(start_point.x, start_point.y, start_point.z)
			gl_ft.glVertex3f(end_point.x, end_point.y, end_point.z)

		# End drawing the vector's lines
		gl_ft.glEnd()

		if text:
			end_point = draw_data.points[1]
			view.drawText(text, end_point)

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		mfn_enum_attr = om.MFnEnumAttribute()
		mfn_comp_attr = om.MFnCompoundAttribute()
		mfn_typed_attr = om.MFnTypedAttribute()
		mfn_matrix_attr = om.MFnMatrixAttribute()

		VectorsVis.upd_parent_matrix_attr = mfn_matrix_attr.create("inPm", "inParentMatrix",
		                                                           om.MFnMatrixAttribute.kDouble)
		mfn_matrix_attr.storable = True
		mfn_matrix_attr.writable = True
		mfn_matrix_attr.keyable = False
		mfn_matrix_attr.default = om.MMatrix().setToIdentity()
		mfn_matrix_attr.affectsAppearance = True

		VectorsVis.line_width_attr = mfn_num_attr.create("width", "lineWidth", om.MFnNumericData.kDouble)
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.keyable = False
		mfn_num_attr.default = DEFAULT_LINE_WIDTH
		mfn_num_attr.affectsAppearance = True

		VectorsVis.arrow_head_size_attr = mfn_num_attr.create("arrowSize", "arrowHeadSize", om.MFnNumericData.kDouble)
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.keyable = False
		mfn_num_attr.default = 1.0
		mfn_num_attr.affectsAppearance = True

		VectorsVis.basis_visible_attr = mfn_enum_attr.create("basis", "showBasis")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 0
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.show_detailed_attr = mfn_enum_attr.create("detailed", "showDetailed")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 0
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.details_font_size_attr = mfn_num_attr.create("detailsFontSize", "detailsFontSize",
		                                                        om.MFnNumericData.kInt)
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.keyable = False
		mfn_num_attr.default = DEF_DETAIL_FONT_SIZE
		mfn_num_attr.affectsAppearance = True

		# Individual vectors' attributes

		vector_label_data = om.MFnStringData().create(VectorsVis.kDefaultVectorLabel)
		VectorsVis.label_attr = mfn_typed_attr.create("label", "vectorLabel", om.MFnData.kString, vector_label_data)
		mfn_typed_attr.affectsAppearance = True

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

		VectorsVis.show_coord_attr = mfn_enum_attr.create("coord", "showCoordinates")
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
		mfn_comp_attr.addChild(VectorsVis.label_attr)
		mfn_comp_attr.addChild(VectorsVis.end_attr)
		mfn_comp_attr.addChild(VectorsVis.color_attr)
		mfn_comp_attr.addChild(VectorsVis.line_style_attr)
		mfn_comp_attr.addChild(VectorsVis.show_coord_attr)
		mfn_comp_attr.addChild(VectorsVis.visible_attr)
		mfn_comp_attr.array = True
		mfn_comp_attr.storable = True
		mfn_comp_attr.writable = True
		mfn_comp_attr.affectsAppearance = True

		VectorsVis.base1_attr = mfn_num_attr.createPoint("base1", "base1")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (VectorsVis.basis_vectors[0].x, VectorsVis.basis_vectors[0].y,
		                        VectorsVis.basis_vectors[0].z)

		VectorsVis.base2_attr = mfn_num_attr.createPoint("base2", "base2")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (VectorsVis.basis_vectors[1].x, VectorsVis.basis_vectors[1].y,
		                        VectorsVis.basis_vectors[1].z)

		VectorsVis.base3_attr = mfn_num_attr.createPoint("base3", "base3")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (VectorsVis.basis_vectors[2].x, VectorsVis.basis_vectors[2].y,
		                        VectorsVis.basis_vectors[2].z)

		VectorsVis.addAttribute(VectorsVis.line_width_attr)
		VectorsVis.addAttribute(VectorsVis.arrow_head_size_attr)
		VectorsVis.addAttribute(VectorsVis.basis_visible_attr)
		VectorsVis.addAttribute(VectorsVis.upd_parent_matrix_attr)
		VectorsVis.addAttribute(VectorsVis.show_detailed_attr)
		VectorsVis.addAttribute(VectorsVis.details_font_size_attr)
		VectorsVis.addAttribute(VectorsVis.in_vectors_data_attr)
		VectorsVis.addAttribute(VectorsVis.base1_attr)
		VectorsVis.addAttribute(VectorsVis.base2_attr)
		VectorsVis.addAttribute(VectorsVis.base3_attr)

		VectorsVis.attributeAffects(VectorsVis.upd_parent_matrix_attr, VectorsVis.base1_attr)
		VectorsVis.attributeAffects(VectorsVis.upd_parent_matrix_attr, VectorsVis.base2_attr)
		VectorsVis.attributeAffects(VectorsVis.upd_parent_matrix_attr, VectorsVis.base3_attr)

	@classmethod
	def creator(cls):
		return cls()

	def compute(self, plug, data_block):
		"""

		:param OpenMaya.MPlug plug:
		:param OpenMaya.MDataBlock data_block:
		"""
		if plug.isChild:
			parent_plug = om.MPlug(plug.parent())
		else:
			parent_plug = plug

		if parent_plug.attribute() == self.base1_attr:
			base_vector = self.basis_vectors[0]
		elif parent_plug.attribute() == self.base2_attr:
			base_vector = self.basis_vectors[1]
		elif parent_plug.attribute() == self.base3_attr:
			base_vector = self.basis_vectors[2]
		else:
			data_block.setClean(plug)
			return

		node_parent_local_matrix = data_block.inputValue(self.upd_parent_matrix_attr).asMatrix()
		base_vector_cp = om.MVector(base_vector)
		base_vector_cp *= node_parent_local_matrix

		plug_data_handle = data_block.outputValue(plug)
		if parent_plug == plug:
			plug_data_handle.set3Float(base_vector_cp.x, base_vector_cp.y, base_vector_cp.z)
		else:
			for child_index in range(3):
				if parent_plug.child(child_index) == plug:
					plug_data_handle.setFloat(base_vector[child_index])
					break

		data_block.setClean(plug)

	def draw(self, view, path, style, status):
		"""

		:param OpenMayaUI.M3dView view:
		:param OpenMaya.MDagPath path:
		:param int style: Style to draw object in. See M3dView.displayStyle() for a list of valid styles.
		:param int status: selection status of object. See M3dView.displayStatus() for a list of valid status.
		:return: Reference to self
		:rtype: VectorsVis
		"""
		shape_path = om.MDagPath(path).extendToShape()
		view_camera_path = view.getCamera()
		vectors_draw_data = [d for d in self.get_vectors_draw_data_from_shape(shape_path, view_camera_path)]
		draw_base_vectors = om.MFnDagNode(shape_path).findPlug(VectorsVis.basis_visible_attr, False).asBool()
		if draw_base_vectors:
			base_vectors_draw_data = self.get_base_vectors_from_shape(shape_path, view_camera_path)
		else:
			base_vectors_draw_data = None

		# Drawing in VP1 views will be done using V1 Python APIs
		import maya.OpenMayaRender as v1omr

		gl_renderer = v1omr.MHardwareRenderer.theRenderer()
		gl_ft = gl_renderer.glFunctionTable()
		gl_ft.glPushAttrib(v1omr.MGL_CURRENT_BIT)

		# Start gl drawing
		view.beginGL()

		# Start drawing the vectors' lines
		for draw_data in vectors_draw_data:
			if draw_data.show_coord:
				end_point = draw_data.points[1]
				text = _coordinates_to_text(end_point)
			else:
				text = None

			self._draw_from_vector_draw_data(draw_data, view, gl_ft, text=text)

		if base_vectors_draw_data:
			for draw_data, axis in zip(base_vectors_draw_data, ['x', 'y', 'z']):
				self._draw_from_vector_draw_data(draw_data, view, gl_ft, text=axis)

		show_details = om.MFnDagNode(shape_path).findPlug(VectorsVis.show_detailed_attr, False).asBool()
		if show_details and view.displayStatus(path) in (omui.M3dView.kLead, omui.M3dView.kActive):
			details_font_size = om.MFnDagNode(shape_path).findPlug(VectorsVis.details_font_size_attr, False).asInt()
			active_view = view.active3dView()
			next_line_y_position = 0
			shape_inv_matrix = shape_path.inclusiveMatrix().inverse()

			# TODO: Currently there is no support for changing the font size for the text

			for vector_data in reversed(vectors_draw_data):
				end_point = vector_data.points[1]
				vector_detail = self.build_vector_detail(vector_data.label, end_point)
				detail_color = vector_data.color
				near_plane_point = om.MPoint()
				far_plane_point = om.MPoint()
				gl_ft.glColor4f(detail_color.r, detail_color.g, detail_color.b, 1.0)

				# The method viewToWorld converts a 2d port point into a 3d world space point on the plane formed by
				# its two point arguments: near and far clip plane. However, the drawText method expects a position
				# in object space. Therefore, the point returned by viewToWorld has to be converted to object space
				# in order to keep the position.
				active_view.viewToWorld(0, next_line_y_position, near_plane_point, far_plane_point)
				view.drawText(vector_detail, (near_plane_point * shape_inv_matrix), view.kLeft)

				next_line_y_position += details_font_size + 5

		# Restore the state
		gl_ft.glPopAttrib()
		view.endGL()
		return self


#######################################################################################################################
#
#  Viewport 2.0 override implementation
#
#######################################################################################################################


class VectorsDrawUserData(om.MUserData):
	_delete_after_user = True
	_camera_path = None
	_vectors_draw_data = None
	_basis_vectors = None
	details = None
	details_font_size = DEF_DETAIL_FONT_SIZE

	def __init__(self, camera_path):
		"""

		:param OpenMaya.MDagPath camera_path:
		"""
		super(VectorsDrawUserData, self).__init__()
		self._camera_path = camera_path
		self._vectors_draw_data = []
		self._basis_vectors = []

	def __eq__(self, other):
		if not type(other) == VectorsDrawUserData:
			return False

		if other.camera_path == self.camera_path and other.draw_data == self.draw_data and other.base_vectors == self.base_vectors:
			return True
		else:
			return False

	@property
	def vectors_arrow_height(self):
		"""

		:rtype: float
		"""
		return DEF_ARROW_HEIGHT

	@property
	def vectors_arrow_base(self):
		"""

		:rtype: float
		"""
		return DEF_ARROW_BASE

	@property
	def draw_data(self):
		"""

		:rtype list[VectorDrawData,]:
		"""
		return self._vectors_draw_data

	@property
	def base_vectors(self):
		"""

		:rtype list[VectorDrawData,]:
		"""
		return self._basis_vectors

	@property
	def camera_path(self):
		"""

		:rtype OpenMaya.MDagPath
		"""
		return self._camera_path

	@camera_path.setter
	def camera_path(self, camera_path):
		"""

		:param OpenMaya.MDagPath camera_path:
		"""
		self._camera_path = camera_path

	def add_vector_draw_data(self, draw_data):
		"""

		:param VectorDrawData draw_data:
		"""

		if not type(draw_data) == VectorDrawData:
			raise TypeError("Expected VectorDrawData. Got {}, instead".format(type(draw_data)))

		self._vectors_draw_data.append(draw_data)

	def add_base_vector_draw_data(self, draw_data):
		"""

		:param VectorDrawData draw_data:
		"""
		if not type(draw_data) == VectorDrawData:
			raise TypeError("Expected VectorDrawData. Got {}, instead".format(type(draw_data)))

		self._basis_vectors.append(draw_data)

	def clear_draw_data(self):
		self._vectors_draw_data = []

	def deleteAfterUser(self):
		"""

		:rtype: bool
		"""
		return self._delete_after_user

	def setDeleteAfterUser(self, delete_after_use):
		"""

		:param bool delete_after_use:
		"""
		self._delete_after_user = delete_after_use


class VectorsVisDrawOverride(VectorsVisMixIn, omr.MPxDrawOverride):
	_draw_apis = omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile | omr.MRenderer.kDirectX11
	_obj = None
	_old_draw_data = None

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
		self._old_draw_data = None

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
		show_base_vectors = mfn_dep_node.findPlug(VectorsVis.basis_visible_attr, False).asBool()
		show_details = mfn_dep_node.findPlug(VectorsVis.show_detailed_attr, False).asBool()
		details_font_size = mfn_dep_node.findPlug(VectorsVis.details_font_size_attr, False).asInt()

		vectors_draw_data = VectorsDrawUserData(camera_path)
		vectors_draw_data.details = show_details
		vectors_draw_data.details_font_size = details_font_size

		for draw_data in self.get_vectors_draw_data_from_shape(obj_path, camera_path):
			vectors_draw_data.add_vector_draw_data(draw_data)

		if show_base_vectors:
			for draw_data in self.get_base_vectors_from_shape(obj_path, camera_path):
				vectors_draw_data.add_base_vector_draw_data(draw_data)

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
		draw_manager.beginDrawable()
		draw_2d = False

		for vector_data in data.draw_data:
			draw_manager.setLineWidth(vector_data.line_width)
			draw_manager.setLineStyle(vector_data.line_style)
			draw_manager.setColor(vector_data.color)
			draw_manager.lineList(om.MPointArray(vector_data.points), draw_2d)

			if vector_data.show_coord:
				end_vector_cp = vector_data.points[1]
				draw_manager.text(end_vector_cp, _coordinates_to_text(end_vector_cp), dynamic=False)

		if data.base_vectors:
			for draw_data, axis in zip(data.base_vectors, ['x', 'y', 'z']):
				draw_manager.setLineWidth(draw_data.line_width)
				draw_manager.setLineStyle(draw_data.line_style)
				draw_manager.setColor(draw_data.color)
				draw_manager.lineList(om.MPointArray(draw_data.points), draw_2d)

				draw_manager.text(draw_data.points[1], axis, dynamic=False)

		if data.details and omui.M3dView.displayStatus(obj_path) in (omui.M3dView.kLead, omui.M3dView.kActive):
			next_line_position = om.MPoint()
			lines_offset_vector = om.MVector(0.0, data.details_font_size, 0.0) + om.MVector(0.0, 5.0, 0.0)
			draw_manager.setFontSize(data.details_font_size)

			for vector_data in reversed(data.draw_data):
				end_point = vector_data.points[1]
				vector_detail = self.build_vector_detail(vector_data.label, end_point)
				draw_manager.setColor(vector_data.color)
				draw_manager.text2d(next_line_position, vector_detail, dynamic=False)
				next_line_position = om.MPoint(om.MVector(next_line_position) + lines_offset_vector)

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
