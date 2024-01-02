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
LOW_LEFT_CORNER_ALIGN = 0
LOW_RIGHT_CORNER_ALIGN = 1
UP_RIGHT_CORNER_ALIGN = 2
UP_LEFT_CORNER_ALIGN = 3
OBJECT_ALIGN = 4
ALIGN_LABELS = [
	("Lower-left corner", LOW_LEFT_CORNER_ALIGN),
	("Lower-right corner", LOW_RIGHT_CORNER_ALIGN),
	("Upper-right corner", UP_RIGHT_CORNER_ALIGN),
	("Upper-left corner", UP_LEFT_CORNER_ALIGN),
	("Object", OBJECT_ALIGN),
]
OBJECT_ALIGN_TO_MAYA = omui.M3dView.kLeft

# RIGHT_ALIGN = 7
# LEFT_ALIGN = 13
# TOP_ALIGN = 14
# BOTTOM_ALIGN = 10


class VectorsVisMixIn(object):
	base_vectors = [om.MVector(1.0, 0.0, 0.0),
	                om.MVector(0.0, 1.0, 0.0),
	                om.MVector(0.0, 0.0, 1.0)]
	base_vectors_labels = ['x', 'y', 'z']

	def __init__(self, *args, **kwargs):
		super(VectorsVisMixIn, self).__init__(*args, **kwargs)

	@staticmethod
	def _coordinates_to_text(point):
		"""

		:param OpenMaya.MPoint|OpenMaya.MVector point:
		:return: Point's coordinates in the format "(x.xxx, x.xxx, x.xxx)".
		:rtype: str
		"""
		trunc_values = []
		for _value in (point.x, point.y, point.z):
			expected_value_length = len("{}".format(math.trunc(_value))) + 3
			_trunc_value_str = "{}".format(math.trunc(_value * 100) / 100)
			while len(_trunc_value_str) < expected_value_length:
				_trunc_value_str += "0"

			trunc_values.append(_trunc_value_str)

		return "({}, {}, {})".format(*trunc_values)

	@staticmethod
	def _build_vector_vis_draw_data(end_point, camera_path, label=DEFAULT_VECTOR_LABEL, arrow_head_scale=1.0,
	                                parent_matrix=None, color=None, line_style=SOLID_STYLE,
	                                line_width=DEFAULT_LINE_WIDTH,
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

		# Project the direction vector onto the camera's plane. Since both base vectors of the camera's plane,
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

	@staticmethod
	def _extract_vectors_data_from_vector_vis_node(vector_vis_shape_path):
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
	def get_vectors_draw_data_from_vector_vis_node(cls, vector_vis_shape_path, camera_path):
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

		for label, end_point, color, line_style, coord_vis in cls._extract_vectors_data_from_vector_vis_node(vector_vis_shape_path):
			yield cls._build_vector_vis_draw_data(end_point, camera_path, label=label,
			                                      arrow_head_scale=arrow_head_scale, parent_matrix=w_trans_matrix,
			                                      color=color, line_style=line_style, line_width=line_width,
			                                      show_coords=coord_vis)

	@classmethod
	def get_base_vectors_draw_data_from_vector_vis_node(cls, vector_vis_shape_path, camera_path):
		"""

		:param OpenMaya.MDagPath vector_vis_shape_path: Path to vectorsVis node
		:param OpenMaya.MDagPath camera_path: Path to current camera
		:return:
		:rtype: iter(VectorDrawData)
		"""
		w_trans_matrix = vector_vis_shape_path.exclusiveMatrix()
		mfn_dep_node = om.MFnDependencyNode(vector_vis_shape_path.node())
		arrow_head_scale = mfn_dep_node.findPlug(VectorsVis.arrow_head_size_attr, False).asDouble()

		for base_vector, color, label in zip(cls.base_vectors, COMPS_COLORS, cls.base_vectors_labels):
			base_point = om.MPoint(base_vector)
			yield cls._build_vector_vis_draw_data(base_point, camera_path, label=label,
			                                      arrow_head_scale=arrow_head_scale, parent_matrix=w_trans_matrix,
			                                      color=color, line_style=SOLID_STYLE, line_width=DEFAULT_LINE_WIDTH,
			                                      show_coords=True)

	@classmethod
	def build_vector_detail(cls, label, end_point):
		"""

		:param str label:
		:param OpenMaya.MPoint end_point:
		:return:
		"rtype: str
		"""
		# Trunc the vector's length to 2 decimal positions and add extra 0's if necessary
		or_length = om.MVector(end_point).length()
		expected_size = len("{}".format(math.trunc(or_length))) + 3
		trunc_length_str = "{}".format(math.trunc(or_length * 100) / 100)
		while len(trunc_length_str) < expected_size:
			trunc_length_str += "0"

		detail = "{} = {}, {}".format(label, cls._coordinates_to_text(end_point), trunc_length_str)
		return detail

	@staticmethod
	def build_matrix_rows_details(matrix):
		"""
		
		:param OpenMaya.MMatrix matrix:
		:return:
		:rtype: iter(tuple(str, OpenMaya.MColor),)
		"""
		columns_values = []
		for col in range(4):
			temp_trunc_col_values = []
			max_length = 0
			for row in range(4):
				value = matrix.getElement(row, col)
				trunc_value_str = "{}".format(math.trunc(value * 100) / 100)
				try:
					__, decimals = trunc_value_str.split(".")
				except ValueError:
					# The value has no decimals
					trunc_value_str = "{}.00".format(trunc_value_str)
				else:
					if len(decimals) < 2:
						trunc_value_str = "{}0".format(trunc_value_str)

				temp_trunc_col_values.append(trunc_value_str)
				if len(trunc_value_str) > max_length:
					max_length = len(trunc_value_str)

			trunc_col_values = []
			for value_str in temp_trunc_col_values:
				while len(value_str) < max_length:
					value_str = " {}".format(value_str)

				trunc_col_values.append(value_str)

			columns_values.append(trunc_col_values)

		row_colors_iter = iter(COMPS_COLORS)
		for row_values in zip(*columns_values):
			try:
				row_color = next(row_colors_iter)
			except StopIteration:
				row_color = om.MColor((0.0, 0.0, 0.0))

			yield " | ".join(row_values), row_color

	@staticmethod
	def text_lines_drawing_port_coord_generator(text_position=LOW_LEFT_CORNER_ALIGN, font_size=DEF_DETAIL_FONT_SIZE, x_offset=None, y_offset=None):
		"""
		Calculates the viewport coordinates (2d) for lines of text based on the alignment received as argument:
		Lower left corner, lower right corner, upper right corner, upper left corner.
		:param int text_position:
		:param int font_size:
		:param int|None x_offset:
		:param int|None y_offset:
		:return: The viewport coordinates (2d) for drawing lines of text, based on the active viewport's resolution.
		:rtype: iter((int, int),)
		"""
		# Return position based on viewport's dimensions
		active_view = omui.M3dView.active3dView()

		# The viewport dimensions are returned in a list with four values. The first two correspond to the
		# lower left corner's x and y coordinates whereas the last two correspond to the upper right corner.
		viewport_dimensions = active_view.viewport()

		if text_position in [LOW_LEFT_CORNER_ALIGN, UP_LEFT_CORNER_ALIGN]:
			text_x_pos = viewport_dimensions[0]
		else:
			text_x_pos = viewport_dimensions[2]

		# TODO: If the text is set to one of the top corners, the font's height has to be removed from the top
		#  corner's y value. Otherwise, the first line of text will not be visible because the text is always drawn
		#  above the point given and there is no way to set its alignment unlike the horizontal alignment.
		if text_position in [UP_LEFT_CORNER_ALIGN, UP_RIGHT_CORNER_ALIGN]:
			text_y_pos = viewport_dimensions[3] - font_size

			# The vertical offset has to be inverted in order for the row of text to be drawn below the given point
			font_size *= -1
		else:
			# The row of text is going to be drawn on the lower part of the viewport. Therefore, we can use the y
			# coordinate of the lower left corner
			text_y_pos = viewport_dimensions[1]

		if x_offset:
			text_x_pos += x_offset
		if y_offset:
			text_y_pos += y_offset

		while True:
			yield text_x_pos, text_y_pos

			text_y_pos += font_size


class VectorsVisCallbackId(om.MUserData):
	_callback_id = None

	def __init__(self):
		super(VectorsVisCallbackId, self).__init__()

	def set_id(self, callback_id):
		self._callback_id = callback_id

	def get_id(self):
		return self._callback_id


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
	show_details_attr = None
	arrow_head_size_attr = None
	details_type_attr = None
	details_font_size_attr = None
	details_align_attr = None
	line_style_attr = None
	visible_attr = None
	show_base_vectors_attr = None
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

	@classmethod
	def _connect_parent_node_matrix_callback(cls, child_path, parent_path, client_data=None):
		"""

		:param OpenMaya.MDagPath child_path:
		:param OpenMaya.MDagPath parent_path:
		:param Any|None client_data:
		"""
		node_mfn_dag = om.MFnDagNode(child_path.node())
		node_parent_matrix_plug = node_mfn_dag.findPlug(cls.upd_parent_matrix_attr, False)
		parent_node_matrix_plug = om.MFnDagNode(parent_path.node()).findPlug("matrix", False)

		m_dag_modifier = om.MDagModifier()
		if node_parent_matrix_plug.isDestination:
			m_dag_modifier.disconnect(node_parent_matrix_plug.source(), node_parent_matrix_plug)

		m_dag_modifier.connect(parent_node_matrix_plug, node_parent_matrix_plug)
		m_dag_modifier.doIt()

	@classmethod
	def _rename_parent_node_callback(cls, child_path, parent_path, client_data=None):
		"""

		:param OpenMaya.MDagPath child_path:
		:param OpenMaya.MDagPath parent_path:
		:param Any|None client_data:
		"""
		node_name = om.MFnDagNode(child_path.node()).name()
		node_number = node_name[len("vectorsVis"):]
		if not node_number:
			node_number = "1"

		m_dag_modifier = om.MDagModifier()
		m_dag_modifier.renameNode(child_path.node(), "vectorsVisShape{}".format(node_number))
		m_dag_modifier.renameNode(parent_path.node(), "vectorsVis{}".format(node_number))
		m_dag_modifier.doIt()

		if client_data and client_data.get_id():
			om.MMessage.removeCallback(client_data.get_id())

	@classmethod
	def _draw_2d_text_lines_on_viewport(cls, gl_ft, text_lines, details_align, shape_matrix_inverse=None, text_lines_colors=None):
		"""

		:param gl_ft:
		:param list text_lines:
		:param int details_align:
		:param list|None text_lines_colors:
		:param OpenMaya.MMatrix|None shape_matrix_inverse: The shape node's world inverse matrix. Necessary for the
			text to stay anchored on the position specified by details_align.
		"""
		if shape_matrix_inverse is None:
			shape_matrix_inverse = om.MMatrix()
			shape_matrix_inverse.setToIdentity()

		if text_lines_colors is None or not len(text_lines_colors) == len(text_lines):
			text_lines_colors = [om.MColor((0, 0, 0)) for __ in range(len(text_lines))]

		# TODO: Currently there is no support for changing the font size for the text. For the moment,
		#  I need to find out how to get the font size that will be used for drawing the text in order
		#  to calculate the vertical offset between lines (including the first line when the alignment
		#  is set to any of the top corners). For the time being, I'm using 12 as the default font size.
		#  This is the value I get when executing the following command: cmds.optionVar(q="smallFontSize")
		details_font_size = DEF_DETAIL_FONT_SIZE

		active_view = omui.M3dView.active3dView()
		active_view_camera_path = active_view.getCamera()
		mfn_camera = om.MFnCamera(active_view_camera_path)
		camera_view_dir = mfn_camera.viewDirection(om.MSpace.kObject)
		near_plane_point = om.MPoint(mfn_camera.nearClippingPlane * camera_view_dir)
		far_plane_point = om.MPoint(mfn_camera.farClippingPlane * camera_view_dir)

		if details_align == OBJECT_ALIGN:
			# Overwrite the details_align original value to the upper left corner. Then, calculate an offset from
			# that corner to the object's projection on the viewport.
			details_align = UP_LEFT_CORNER_ALIGN
			viewport_dim = active_view.viewport()
			x_offset, y_offset, __ = active_view.worldToView(om.MPoint() * shape_matrix_inverse.inverse())
			y_offset -= viewport_dim[3]
		else:
			x_offset = y_offset = 0

		maya_text_align = omui.M3dView.kLeft if details_align in [LOW_LEFT_CORNER_ALIGN, UP_LEFT_CORNER_ALIGN] else omui.M3dView.kRight
		details_rows_start_iter = cls.text_lines_drawing_port_coord_generator(text_position=details_align,
		                                                                      font_size=details_font_size + 5,
		                                                                      x_offset=x_offset, y_offset=y_offset)

		# When the details' table is displayed in the lower area of the viewport, it's easier to draw it
		# from the bottom up. To do this, the vector's order has to be reversed so the details for the
		# last vector are drawn first and those for the first vector are drawn last.
		if details_align in [LOW_LEFT_CORNER_ALIGN, LOW_RIGHT_CORNER_ALIGN]:
			text_lines = reversed(text_lines)
			text_lines_colors = reversed(text_lines_colors)

		for i, line_data in enumerate(zip(text_lines, text_lines_colors)):
			line, line_color = line_data
			near_plane_point_cp = om.MPoint(near_plane_point)
			far_plane_point_cp = om.MPoint(far_plane_point)

			if line_color:
				gl_ft.glColor4f(line_color.r, line_color.g, line_color.b, 1.0)

			# The method viewToWorld converts a 2d port point into a 3d world space point on the plane formed by
			# its two point arguments: near and far clip plane. However, the drawText method expects a position
			# in object space. Therefore, the point returned by viewToWorld has to be converted to object space
			# in order to keep the position.
			text_x_pos, text_y_pos = next(details_rows_start_iter)
			active_view.viewToWorld(text_x_pos, text_y_pos, near_plane_point_cp, far_plane_point_cp)
			active_view.drawText(line, near_plane_point_cp * shape_matrix_inverse, maya_text_align)

	@classmethod
	def _draw_vectors_details_on_viewport(cls, gl_ft, vectors_draw_data, details_align, local_matrix_inverse):
		"""

		:param gl_ft:
		:param list(VectorDrawData) vectors_draw_data:
		:param int details_align:
		:param OpenMaya.MMatrix local_matrix_inverse:
		"""

		vectors_details = []
		vectors_details_colors = []
		for draw_data in vectors_draw_data:
			detail = cls.build_vector_detail(draw_data.label, draw_data.points[1])
			vectors_details.append(detail)
			vectors_details_colors.append(draw_data.color)

		cls._draw_2d_text_lines_on_viewport(gl_ft, vectors_details, details_align, local_matrix_inverse,
		                                    text_lines_colors=vectors_details_colors)

	@classmethod
	def _draw_matrix_details_on_viewport(cls, gl_ft, matrix, details_align, local_matrix_inverse):
		"""

		:param gl_ft:
		:param OpenMaya.MMatrix matrix:
		:param int details_align:
		:param OpenMaya.MMatrix local_matrix_inverse:
		"""
		rows_values = []
		rows_colors = []
		for row_str, row_color in cls.build_matrix_rows_details(matrix):
			rows_values.append(row_str)
			rows_colors.append(row_color)

		cls._draw_2d_text_lines_on_viewport(gl_ft, rows_values, details_align, local_matrix_inverse,
		                                    text_lines_colors=rows_colors)

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

		VectorsVis.show_base_vectors_attr = mfn_enum_attr.create("showBaseVectors", "showBaseVectors")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 0
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.show_details_attr = mfn_enum_attr.create("showDetails", "showDetailes")
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

		VectorsVis.details_align_attr = mfn_enum_attr.create("detailsAlign", "detailsAlign")
		for align_label, align_value in ALIGN_LABELS:
			mfn_enum_attr.addField(align_label, align_value)

		mfn_enum_attr.storable = True
		mfn_enum_attr.writable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.affectsAppearance = True

		VectorsVis.details_type_attr = mfn_enum_attr.create("detailsType", "detailsType")
		mfn_enum_attr.addField("Vectors", 0)
		mfn_enum_attr.addField("Matrix", 1)
		mfn_enum_attr.storable = True
		mfn_enum_attr.writable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.affectsAppearance = True

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
		mfn_num_attr.default = (VectorsVis.base_vectors[0].x, VectorsVis.base_vectors[0].y,
		                        VectorsVis.base_vectors[0].z)

		VectorsVis.base2_attr = mfn_num_attr.createPoint("base2", "base2")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (VectorsVis.base_vectors[1].x, VectorsVis.base_vectors[1].y,
		                        VectorsVis.base_vectors[1].z)

		VectorsVis.base3_attr = mfn_num_attr.createPoint("base3", "base3")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (VectorsVis.base_vectors[2].x, VectorsVis.base_vectors[2].y,
		                        VectorsVis.base_vectors[2].z)

		VectorsVis.addAttribute(VectorsVis.line_width_attr)
		VectorsVis.addAttribute(VectorsVis.arrow_head_size_attr)
		VectorsVis.addAttribute(VectorsVis.show_base_vectors_attr)
		VectorsVis.addAttribute(VectorsVis.show_details_attr)
		VectorsVis.addAttribute(VectorsVis.details_type_attr)
		VectorsVis.addAttribute(VectorsVis.details_align_attr)
		VectorsVis.addAttribute(VectorsVis.details_font_size_attr)
		VectorsVis.addAttribute(VectorsVis.upd_parent_matrix_attr)
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

	def postConstructor(self):
		node_path = om.MFnDagNode(self.thisMObject()).getPath()
		om.MDagMessage.addParentAddedDagPathCallback(node_path, self._connect_parent_node_matrix_callback, None)

		callbacks_user_data = VectorsVisCallbackId()
		rename_parent_cb_id = om.MDagMessage.addParentAddedDagPathCallback(node_path,
		                                                                   self._rename_parent_node_callback,
		                                                                   callbacks_user_data)
		callbacks_user_data.set_id(rename_parent_cb_id)

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
			base_vector = self.base_vectors[0]
		elif parent_plug.attribute() == self.base2_attr:
			base_vector = self.base_vectors[1]
		elif parent_plug.attribute() == self.base3_attr:
			base_vector = self.base_vectors[2]
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

	def draw(self, view, shape_parent_path, style, status):
		"""

		:param OpenMayaUI.M3dView view:
		:param OpenMaya.MDagPath shape_parent_path:
		:param int style: Style to draw object in. See M3dView.displayStyle() for a list of valid styles.
		:param int status: selection status of object. See M3dView.displayStatus() for a list of valid status.
		:return: Reference to self
		:rtype: VectorsVis
		"""
		shape_path = om.MDagPath(shape_parent_path).extendToShape()
		mfn_shape_dag_node = om.MFnDagNode(shape_path)
		view_camera_path = view.getCamera()
		vectors_draw_data = [d for d in self.get_vectors_draw_data_from_vector_vis_node(shape_path, view_camera_path)]
		draw_base_vectors = mfn_shape_dag_node.findPlug(VectorsVis.show_base_vectors_attr, False).asBool()
		if draw_base_vectors:
			base_vectors_draw_data = [d for d in self.get_base_vectors_draw_data_from_vector_vis_node(shape_path, view_camera_path)]
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
				text = self._coordinates_to_text(end_point)
			else:
				text = None

			self._draw_from_vector_draw_data(draw_data, view, gl_ft, text=text)

		if base_vectors_draw_data:
			for draw_data in base_vectors_draw_data:
				self._draw_from_vector_draw_data(draw_data, view, gl_ft, text=draw_data.label)

		show_details = mfn_shape_dag_node.findPlug(VectorsVis.show_details_attr, False).asBool()
		shape_selected = view.displayStatus(shape_path) in (omui.M3dView.kLead, omui.M3dView.kActive)
		shape_parent_selected = view.displayStatus(shape_parent_path) in (omui.M3dView.kLead, omui.M3dView.kActive)

		if show_details and (shape_selected or shape_parent_selected):
			details_type = mfn_shape_dag_node.findPlug(VectorsVis.details_type_attr, False).asInt()
			details_align = mfn_shape_dag_node.findPlug(VectorsVis.details_align_attr, False).asInt()
			shape_inv_matrix = shape_path.inclusiveMatrix().inverse()

			if details_type == 0:
				self._draw_vectors_details_on_viewport(gl_ft, vectors_draw_data, details_align, shape_inv_matrix)
			else:
				mfn_parent_dep = om.MFnDependencyNode(shape_parent_path.node())
				parent_obj_matrix = om.MFnMatrixData(mfn_parent_dep.findPlug("matrix", False).asMObject()).matrix()

				self._draw_matrix_details_on_viewport(gl_ft, parent_obj_matrix, details_align, shape_inv_matrix)

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
	_base_vectors = None
	_details_type = 0
	_details_align = LOW_LEFT_CORNER_ALIGN
	_matrix = None
	details = False
	details_font_size = DEF_DETAIL_FONT_SIZE

	def __init__(self, camera_path):
		"""

		:param OpenMaya.MDagPath camera_path:
		"""
		super(VectorsDrawUserData, self).__init__()
		self._camera_path = camera_path
		self._vectors_draw_data = []
		self._base_vectors = []

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
		return self._base_vectors

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

	@property
	def details_align(self):
		return self._details_align

	@details_align.setter
	def details_align(self, details_align):
		if details_align not in [value for _, value in ALIGN_LABELS]:
			return

		self._details_align = details_align

	@property
	def details_type(self):
		return self._details_type

	@details_type.setter
	def details_type(self, details_type):
		if details_type not in [0, 1]:
			return

		self._details_type = details_type

	@property
	def matrix(self):
		return self._matrix

	@matrix.setter
	def matrix(self, matrix):
		if not isinstance(matrix, om.MMatrix):
			return

		self._matrix = matrix

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

		self._base_vectors.append(draw_data)

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

	def prepareForDraw(self, vector_vis_node_path, camera_path, frame_context, old_data):
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

		:param OpenMaya.MDagPath vector_vis_node_path:
		:param OpenMaya.MDagPath camera_path:
		:param OpenMayaRender.MFrameContext frame_context:
		:param OpenMaya.MUserData old_data:
		:return: The data to be passed to the draw callback method
		:rtype: VectorsDrawUserData
		"""
		mfn_vectors_vis_node = om.MFnDependencyNode(vector_vis_node_path.node())
		mfn_dep_parent = om.MFnDependencyNode(vector_vis_node_path.transform())
		show_base_vectors = mfn_vectors_vis_node.findPlug(VectorsVis.show_base_vectors_attr, False).asBool()
		show_details = mfn_vectors_vis_node.findPlug(VectorsVis.show_details_attr, False).asBool()
		details_type = mfn_vectors_vis_node.findPlug(VectorsVis.details_type_attr, False).asInt()
		details_font_size = mfn_vectors_vis_node.findPlug(VectorsVis.details_font_size_attr, False).asInt()
		details_align = mfn_vectors_vis_node.findPlug(VectorsVis.details_align_attr, False).asInt()

		vectors_draw_data = VectorsDrawUserData(camera_path)
		vectors_draw_data.details = show_details
		vectors_draw_data.details_type = details_type
		vectors_draw_data.details_font_size = details_font_size
		vectors_draw_data.details_align = details_align
		vectors_draw_data.matrix = om.MFnMatrixData(mfn_dep_parent.findPlug(VectorsVis.matrix, False).asMObject()).matrix()

		for draw_data in self.get_vectors_draw_data_from_vector_vis_node(vector_vis_node_path, camera_path):
			vectors_draw_data.add_vector_draw_data(draw_data)

		if show_base_vectors:
			for draw_data in self.get_base_vectors_draw_data_from_vector_vis_node(vector_vis_node_path, camera_path):
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
		:return: Reference to self
		:rtype: VectorsVisDrawOverride
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
				draw_manager.text(end_vector_cp, self._coordinates_to_text(end_vector_cp), dynamic=False)

		if data.base_vectors:
			for draw_data, axis in zip(data.base_vectors, ['x', 'y', 'z']):
				draw_manager.setLineWidth(draw_data.line_width)
				draw_manager.setLineStyle(draw_data.line_style)
				draw_manager.setColor(draw_data.color)
				draw_manager.lineList(om.MPointArray(draw_data.points), draw_2d)

				draw_manager.text(draw_data.points[1], axis, dynamic=False)

		if data.details and omui.M3dView.displayStatus(obj_path) in (omui.M3dView.kLead, omui.M3dView.kActive):
			vectors_details = data.draw_data
			details_align = data.details_align
			details_type = data.details_type

			if details_align == OBJECT_ALIGN:
				# Overwrite the details_align original value to the upper left corner. Then, calculate an offset from
				# that corner to the object's projection on the viewport.
				details_align = UP_LEFT_CORNER_ALIGN
				active_view = omui.M3dView.active3dView()
				x_offset, y_offset, __ = active_view.worldToView(om.MPoint() * obj_path.inclusiveMatrix())
				y_offset -= active_view.viewport()[3]
			else:
				x_offset = y_offset = 0

			draw_in_lower_half = details_align in [LOW_LEFT_CORNER_ALIGN, LOW_RIGHT_CORNER_ALIGN]
			details_rows_start_iter = self.text_lines_drawing_port_coord_generator(text_position=details_align,
			                                                                       font_size=data.details_font_size + 5,
			                                                                       x_offset=x_offset, y_offset=y_offset)
			maya_text_align = omr.MUIDrawManager.kLeft if details_align in [LOW_LEFT_CORNER_ALIGN,
			                                                                UP_LEFT_CORNER_ALIGN] else omr.MUIDrawManager.kRight

			draw_manager.setFontSize(data.details_font_size)

			if details_type == 0:
				# When the details' table is displayed in the lower area of the viewport, it's easier to draw it
				# from the bottom up. To do this, the vector's order has to be reversed so the details for the
				# last vector are drawn first and those for the first vector are drawn last.
				if draw_in_lower_half:
					vectors_details = reversed(data.draw_data)

				for vector_data in vectors_details:
					end_point = vector_data.points[1]
					vector_detail = self.build_vector_detail(vector_data.label, end_point)
					text_x_pos, text_y_pos = next(details_rows_start_iter)
					next_line_point = om.MPoint(text_x_pos, text_y_pos, 0.0)

					draw_manager.setColor(vector_data.color)
					draw_manager.text2d(next_line_point, vector_detail, alignment=maya_text_align, dynamic=False)
			elif details_type == 1:
				matrix_details = self.build_matrix_rows_details(data.matrix)

				# When the details' table is displayed in the lower area of the viewport, it's easier to draw it
				# from the bottom up. To do this, the vector's order has to be reversed so the details for the
				# last vector are drawn first and those for the first vector are drawn last.
				if draw_in_lower_half:
					matrix_details = reversed([d for d in matrix_details])

				for row_details, row_color in matrix_details:
					text_x_pos, text_y_pos = next(details_rows_start_iter)
					next_line_point = om.MPoint(text_x_pos, text_y_pos, 0.0)

					draw_manager.setColor(row_color)
					draw_manager.text2d(next_line_point, row_details, alignment=maya_text_align,
					                    dynamic=False)

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
