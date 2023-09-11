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

PLANES_BASES = [((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
                ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))]

MayaAttrSpecs = namedtuple('MayaAttrSpecs', ['short', 'long', 'type', 'min', 'max', 'default',
                                             'keyable', 'storable', 'writable'])


def space_vis_points(range_scale=1, planes_bases=None):
	min_lines = 1
	lines_per_side = min_lines * range_scale
	rows_count = cols_count = (lines_per_side * 2) + 1
	vtx_points = []
	vtx_normals = []

	if not planes_bases:
		planes_bases = PLANES_BASES

	for base_a, base_b in planes_bases:
		normal_vector = om.MVector(base_a) ^ om.MVector(base_b)
		normal = (normal_vector.x, normal_vector.y, normal_vector.z)
		# Calculate the points from positive to negative in both directions: vertically and horizontally
		for j in range(lines_per_side, lines_per_side - rows_count, -1):
			base_b_scaled = [c * j for c in base_b]
			for i in range(lines_per_side * -1, cols_count - lines_per_side, 1):
				vtx_points.append([(co * i) + base_b_scaled[co_i] for co_i, co in enumerate(base_a)])
				# Save a copy of the normal for the plane for each calculated point
				vtx_normals.append(normal)

	return vtx_points, vtx_normals


def get_rows_cols_count(points_count):
	planes_points_count = points_count / 3
	rows_count = cols_count = math.sqrt(planes_points_count)
	print(">> {} x {} for {}".format(rows_count, cols_count, points_count))
	return int(rows_count), int(cols_count)


def space_vis_geo_sets(rows_count, cols_count):
	tri_points = []
	lines_points = []

	for plane_index in range(3):
		plane_off = rows_count * cols_count * plane_index
		plane_tri_points = [
			plane_off,
			plane_off + cols_count - 1,
			plane_off + (rows_count * (cols_count - 1)),
			plane_off + (rows_count * (cols_count - 1)),
			plane_off + (rows_count * cols_count) - 1,
			plane_off + cols_count - 1
		]
		plane_lines_points = []
		# Calculate the horizontal lines
		for i in range(plane_off, plane_off + (rows_count * cols_count), cols_count):
			for j in range(i, i + cols_count - 1, 1):
				plane_lines_points.append((j, j + 1))

		# Calculate the vertical lines
		for i in range(plane_off, plane_off + rows_count * (cols_count - 1), cols_count):
			for j in range(cols_count):
				plane_lines_points.append((i + j, i + j + cols_count))

		tri_points.append(plane_tri_points)
		lines_points.append(plane_lines_points)

	return lines_points, tri_points


class SpaceVisMixIn(object):
	_origin_offset_blend = None
	_planes_scale = None
	_origin_offset_matrix = None

	PLANES_NAMES = ["xyPlane", "xzPlane", "yzPlane"]
	PLANES_ITEMS_COLORS = [
		((25.5, 51.0, 255.0, 255.0), (0.0, 25.5, 178.5, 255.0)),
		((51.0, 255.0, 25.5, 255.0), (25.5, 178.5, 0.0, 255.0)),
		((153.0, 51.0, 20.4, 255.0), (178.5, 0.0, 25.5, 255.0))
	]

	PLANE_XY_BASE1_SPECS = MayaAttrSpecs("xyBase1", "xyBase1",
	                                     om.MFnNumericData.k3Double,
	                                     None, None, PLANES_BASES[0][0],
	                                     True, True, True)
	PLANE_XY_BASE2_SPECS = MayaAttrSpecs("xyBase2", "xyBase2",
	                                     om.MFnNumericData.k3Double,
	                                     None, None, PLANES_BASES[0][1],
	                                     True, True, True)
	PLANE_XZ_BASE1_SPECS = MayaAttrSpecs("xzBase1", "xzBase1",
	                                     om.MFnNumericData.k3Double,
	                                     None, None, PLANES_BASES[1][0],
	                                     True, True, True)
	PLANE_XZ_BASE2_SPECS = MayaAttrSpecs("xzBase2", "xzBase2",
	                                     om.MFnNumericData.k3Double,
	                                     None, None, PLANES_BASES[1][1],
	                                     True, True, True)
	PLANE_YZ_BASE1_SPECS = MayaAttrSpecs("yzBase1", "yzBase1",
	                                     om.MFnNumericData.k3Double,
	                                     None, None, PLANES_BASES[2][0],
	                                     True, True, True)
	PLANE_YZ_BASE2_SPECS = MayaAttrSpecs("yzBase2", "yzBase2",
	                                     om.MFnNumericData.k3Double,
	                                     None, None, PLANES_BASES[2][1],
	                                     True, True, True)
	PLANES_SCALE_SPECS = MayaAttrSpecs("planesScale", "planesScale",
	                                   om.MFnNumericData.kShort,
	                                   1, None, 1,
	                                   True, True, True)
	ORIGIN_OFFSET_BLEND_SPECS = MayaAttrSpecs("offsetBlend", "spaceOriginOffsetBlend",
	                                          om.MFnNumericData.kDouble,
	                                          0.0, 1.0, 1.0,
	                                          True, True, True)
	ORIGIN_OFFSET_MATRIX_SPECS = MayaAttrSpecs("originOffset", "spaceOriginOffsetMatrix",
	                                           om.MFnMatrixAttribute.kDouble,
	                                           None, None, om.MMatrix().setToIdentity(),
	                                           False, True, True)

	SPACE_POINTS_SPECS = MayaAttrSpecs("points", "spacePoints",
	                                   om.MFnNumericData.k3Double,
	                                   None, None, None,
	                                   False, True, False)
	OFFSET_SPACE_POINTS_SPECS = MayaAttrSpecs("offPoints", "offsetPoints",
	                                          om.MFnNumericData.k3Double,
	                                          None, None, None,
	                                          False, True, False)
	LINES_POINTS_IDS_SPECS = MayaAttrSpecs("linesPointsIds", "linesPointsIds",
	                                       om.MFnNumericData.k2Int,
	                                       None, None, None,
	                                       False, True, False)
	TRIS_POINTS_IDS_SPECS = MayaAttrSpecs("triPointsIds", "trianglesPointsIds",
	                                      om.MFnNumericData.k2Int,
	                                      None, None, None,
	                                      False, True, False)

	vtx_points_backup = None
	vtx_points = None
	lines_points_ids = None
	tri_points_ids = None
	vtx_normals_vectors = None
	plane_tris_count = None

	xy_bases = None
	xz_bases = None
	yz_bases = None

	def __init__(self, *args, **kwargs):
		super(SpaceVisMixIn, self).__init__(*args, **kwargs)

		self._planes_scale = self.PLANES_SCALE_SPECS.default
		self.xy_bases = (self.PLANE_XY_BASE1_SPECS.default, self.PLANE_XY_BASE2_SPECS.default)
		self.xz_bases = (self.PLANE_XZ_BASE1_SPECS.default, self.PLANE_XZ_BASE2_SPECS.default)
		self.yz_bases = (self.PLANE_YZ_BASE1_SPECS.default, self.PLANE_YZ_BASE2_SPECS.default)

		planes_bases = [self.xy_bases, self.xz_bases, self.yz_bases]
		self.vtx_points_backup, self.vtx_normals_vectors = space_vis_points(self._planes_scale,
		                                                                    planes_bases=planes_bases)
		self.vtx_points = [point for point in self.vtx_points_backup]
		self.lines_points_ids, self.tri_points_ids = space_vis_geo_sets(*get_rows_cols_count(len(self.vtx_points)))

	@property
	def planes_scale(self):
		return self._planes_scale

	@planes_scale.setter
	def planes_scale(self, scale):
		self._planes_scale = scale

	@property
	def origin_offset_blend(self):
		return self._origin_offset_blend

	@origin_offset_blend.setter
	def origin_offset_blend(self, offset_vector):
		self._origin_offset_blend = offset_vector

	@property
	def origin_offset_matrix(self):
		return self._origin_offset_matrix

	@origin_offset_matrix.setter
	def origin_offset_matrix(self, offset_matrix):
		self._origin_offset_matrix = offset_matrix

	def update_points(self, planes_scale=None, origin_offset_blend=None, origin_offset_matrix=None):
		pass


class SpaceVis(SpaceVisMixIn, omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/spaceVis"
	drawRegistrantId = "SpaceVisPlugin"
	typeId = om.MTypeId(0x80006)

	yz_base1_attr = None
	yz_base2_attr = None
	xz_base1_attr = None
	xz_base2_attr = None
	xy_base1_attr = None
	xy_base2_attr = None
	planes_scale_attr = None
	origin_off_blend_attr = None
	origin_off_matrix_attr = None

	points_attr = None
	offset_points_attr = None
	lines_points_ids_attr = None
	tri_points_ids_attr = None

	def __init__(self):
		super(SpaceVis, self).__init__()

		# Normalize the planes' colors values
		normalized_planes_colors = []
		for plane_colors in self.PLANES_ITEMS_COLORS:
			shaded_color, wire_color = plane_colors
			normal_shaded_color = [val / 255.0 for val in shaded_color]
			normal_wire_color = [val / 255.0 for val in wire_color]
			normalized_planes_colors.append((tuple(normal_shaded_color), tuple(normal_wire_color)))

		self.PLANES_ITEMS_COLORS = tuple(normalized_planes_colors)

	@classmethod
	def __create_attribute(cls, mfn, maya_attr_specs):
		"""

		:param OpenMaya.MFn mfn:
		:param MayaAttrSpecs maya_attr_specs:
		:return:
		:rtype: OpenMaya.MObject
		"""
		mfn.create(maya_attr_specs.short,
		           maya_attr_specs.long,
		           maya_attr_specs.type)

		if maya_attr_specs.min is not None:
			mfn.setMin(maya_attr_specs.min)
		if maya_attr_specs.max is not None:
			mfn.setMax(maya_attr_specs.max)
		if maya_attr_specs.default is not None:
			mfn.default = maya_attr_specs.default

		mfn.keyable = maya_attr_specs.keyable
		mfn.storable = maya_attr_specs.storable
		mfn.writable = maya_attr_specs.writable

		# All custom attributes affect the appearance since they modify either the number of points
		# or their positions
		mfn.affectsAppearance = True

		cls.addAttribute(mfn.object())

		return mfn.object()

	@classmethod
	def creator(cls):
		return cls()

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		mfn_matrix_attr = om.MFnMatrixAttribute()

		SpaceVis.planes_scale_attr = SpaceVis.__create_attribute(mfn_num_attr, SpaceVis.PLANES_SCALE_SPECS)

		# Create the space offset attribute
		SpaceVis.origin_off_blend_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                             SpaceVis.ORIGIN_OFFSET_BLEND_SPECS)

		# Create the offset origin matrix attribute
		SpaceVis.origin_off_matrix_attr = SpaceVis.__create_attribute(mfn_matrix_attr,
		                                                              SpaceVis.ORIGIN_OFFSET_MATRIX_SPECS)

		SpaceVis.yz_base1_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                     SpaceVis.PLANE_YZ_BASE1_SPECS)
		SpaceVis.yz_base2_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                     SpaceVis.PLANE_YZ_BASE2_SPECS)

		SpaceVis.xz_base1_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                     SpaceVis.PLANE_XZ_BASE1_SPECS)
		SpaceVis.xz_base2_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                     SpaceVis.PLANE_XZ_BASE2_SPECS)

		SpaceVis.xy_base1_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                     SpaceVis.PLANE_XY_BASE1_SPECS)
		SpaceVis.xy_base2_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                     SpaceVis.PLANE_XY_BASE2_SPECS)

		# TODO: Remove these output plugs since they are not needed
		# Create output plugs
		SpaceVis.points_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                   SpaceVis.SPACE_POINTS_SPECS)
		mfn_num_attr.array = True

		SpaceVis.offset_points_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                          SpaceVis.OFFSET_SPACE_POINTS_SPECS)
		mfn_num_attr.array = True

		SpaceVis.lines_points_ids_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                             SpaceVis.LINES_POINTS_IDS_SPECS)
		mfn_num_attr.array = True

		SpaceVis.tri_points_ids_attr = SpaceVis.__create_attribute(mfn_num_attr,
		                                                           SpaceVis.TRIS_POINTS_IDS_SPECS)
		mfn_num_attr.array = True

		SpaceVis.attributeAffects(SpaceVis.planes_scale_attr, SpaceVis.points_attr)
		SpaceVis.attributeAffects(SpaceVis.planes_scale_attr, SpaceVis.offset_points_attr)
		SpaceVis.attributeAffects(SpaceVis.planes_scale_attr, SpaceVis.lines_points_ids_attr)
		SpaceVis.attributeAffects(SpaceVis.planes_scale_attr, SpaceVis.tri_points_ids_attr)

		for base_attr in [SpaceVis.yz_base1_attr, SpaceVis.yz_base2_attr,
		                  SpaceVis.xy_base1_attr, SpaceVis.xy_base2_attr,
		                  SpaceVis.xz_base1_attr, SpaceVis.xz_base2_attr]:
			SpaceVis.attributeAffects(base_attr, SpaceVis.points_attr)
			SpaceVis.attributeAffects(base_attr, SpaceVis.offset_points_attr)

		SpaceVis.attributeAffects(SpaceVis.origin_off_blend_attr, SpaceVis.offset_points_attr)
		SpaceVis.attributeAffects(SpaceVis.origin_off_matrix_attr, SpaceVis.offset_points_attr)

	def compute(self, plug, data_block):
		"""

		:param plug: OpenMaya.MPlug instance
		:param data_block: OpenMaya.MDataBlock instance
		"""
		print(">> From compute... {}".format(plug.name()))
		if plug.attribute() not in [self.planes_scale_attr, self.xy_base1_attr, self.xy_base2_attr,
		                            self.xz_base1_attr, self.xz_base2_attr, self.yz_base1_attr,
		                            self.yz_base2_attr, self.origin_off_blend_attr, self.origin_off_matrix_attr]:
			data_block.setClean(plug)
			return

		if plug.attribute() in [self.planes_scale_attr, self.xy_base1_attr, self.xy_base2_attr, self.xz_base1_attr,
		                        self.xz_base2_attr, self.yz_base1_attr, self.yz_base2_attr]:
			xy_base1 = data_block.inputValue(self.xy_base1_attr).asFloat3()
			xy_base2 = data_block.inputValue(self.xy_base2_attr).asFloat3()
			xz_base1 = data_block.inputValue(self.xz_base1_attr).asFloat3()
			xz_base2 = data_block.inputValue(self.xz_base2_attr).asFloat3()
			yz_base1 = data_block.inputValue(self.yz_base1_attr).asFloat3()
			yz_base2 = data_block.inputValue(self.yz_base2_attr).asFloat3()
			planes_bases = [(xy_base1, xy_base2), (xz_base1, xz_base2), (yz_base1, yz_base2)]
			planes_scale = data_block.inputValue(self.planes_scale_attr).asInt()

			self.vtx_points_backup, self.vtx_normals_vectors = space_vis_points(planes_scale,
			                                                                    planes_bases=planes_bases)
			self.vtx_points = [point for point in self.vtx_points_backup]
			if plug.attribute() == self.planes_scale_attr:
				# If the planes' scale changed, this means the number of points changed. Therefore, all the
				# geo's ids have to be updated as well
				self.lines_points_ids, self.tri_points_ids = space_vis_geo_sets(*get_rows_cols_count(len(self.vtx_points)))

			points_array_data_handle = data_block.outputArrayValue(self.points_attr)
			for point_index, point in enumerate(self.vtx_points_backup):
				point_data_handle = points_array_data_handle.jumpToPhysicalElement(point_index).outputValue()
				point_data_handle.set3Double(*point)

		# Space offset changed. This means points have changed but remain the same total number
		origin_offset_blend = data_block.inputValue(self.origin_off_blend_attr).asDouble()
		origin_offset_matrix = data_block.inputValue(self.origin_off_matrix_attr).asMatrix()

		parent_trans_inv_matrix = om.MTransformationMatrix(origin_offset_matrix)
		parent_inv_pos_vector = parent_trans_inv_matrix.translation(om.MSpace.kWorld)
		parent_inv_pos_scaled_vector = parent_inv_pos_vector * (1.0 - origin_offset_blend)

		# Scale the parent inverse position vector
		parent_w_inv_pos = (parent_inv_pos_scaled_vector.x,
		                    parent_inv_pos_scaled_vector.y,
		                    parent_inv_pos_scaled_vector.z)

		self.vtx_points = [vector_add((point, parent_w_inv_pos)) for point in self.vtx_points_backup]
		self.origin_offset_blend = origin_offset_blend
		self.origin_offset_matrix = origin_offset_matrix

		off_points_array_data_handle = data_block.outputArrayValue(self.offset_points_attr)
		for off_point_index, off_point in enumerate(self.vtx_points):
			off_point_data_handle = off_points_array_data_handle.jumpToPhysicalElement(off_point_index).outputValue()
			off_point_data_handle.set3Double(*off_point)

		data_block.setClean(plug)

	def draw(self, view, path, style, status):
		# Drawing in VP1 views will be done using V1 Python APIs
		import maya.OpenMayaRender as v1omr

		# Start gl drawing
		view.beginGL()

		gl_renderer = v1omr.MHardwareRenderer.theRenderer()
		gl_ft = gl_renderer.glFunctionTable()

		if (style == omui.M3dView.kFlatShaded) or (style == omui.M3dView.kGouraudShaded):
			gl_ft.glPushAttrib(v1omr.MGL_CURRENT_BIT)
			gl_ft.glDisable(v1omr.MGL_CULL_FACE)
		if status == omui.M3dView.kActive:
			view.setDrawColor(10, omui.M3dView.kActiveColors)
		else:
			view.setDrawColor(9, omui.M3dView.kDormantColors)

		# Enable transparency
		gl_ft.glEnable(v1omr.MGL_BLEND)

		# Start drawing the planes' lines
		gl_ft.glBegin(v1omr.MGL_LINES)

		for plane_points_ids, plane_color in zip(self.lines_points_ids, self.PLANES_ITEMS_COLORS):
			# Set the planes' line color accordingly
			gl_ft.glColor4f(*plane_color[1])

			for start_id, end_id in plane_points_ids:
				gl_ft.glVertex3f(*self.vtx_points[start_id])
				gl_ft.glVertex3f(*self.vtx_points[end_id])

		# End drawing the planes' lines
		gl_ft.glEnd()

		# Start drawing the planes' triangle faces
		# Push the color settings
		gl_ft.glPushAttrib(v1omr.MGL_CURRENT_BIT)

		# Show both faces
		gl_ft.glDisable(v1omr.MGL_CULL_FACE)

		view.setDrawColor(13, omui.M3dView.kActiveColors)

		for plane_points_ids, plane_color in zip(self.tri_points_ids, self.PLANES_ITEMS_COLORS):
			# Set the planes' line color accordingly
			gl_ft.glColor4f(*plane_color[0])

			gl_ft.glBegin(v1omr.MGL_TRIANGLE_FAN)

			for point_index, point_id in enumerate(plane_points_ids):
				if point_index > 0 and point_index % 3 == 0:
					continue
				gl_ft.glVertex3f(*self.vtx_points[point_id])

			gl_ft.glEnd()

		gl_ft.glPopAttrib()
		# End drawing the bind\'s triangle faces

		# Disable transparency
		gl_ft.glDisable(v1omr.MGL_BLEND)

		view.endGL()

	def isBounded(self):
		return True

	def boundingBox(self):
		bbox = om.MBoundingBox(om.MPoint(0.5, 0.5, 0.5), om.MPoint(-0.5, -0.5, -0.5))
		return bbox


#######################################################################################################################
#
#  Viewport 2.0 override implementation
#
#######################################################################################################################

RenderItemSpec = namedtuple('RenderItemSpec', ['name', 'geo_type', 'draw_mode', 'shader'])


class SpaceVisData(om.MUserData):
	def __init__(self):
		# The boolean argument tells Maya to don\'t delete the data after draw
		super(SpaceVisData, self).__init__(False)


class SpaceVisGeometryOverride(SpaceVisMixIn, omr.MPxGeometryOverride):
	_obj = None
	_render_items_specs = None
	_stream_dirty = False
	_draw_apis = omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile | omr.MRenderer.kDirectX11

	def __init__(self, obj):
		super(SpaceVisGeometryOverride, self).__init__(obj)

		self._render_items_specs = []
		self._obj = obj

		# Normalize colors values
		normal_colors = []
		for shaded_color, wire_color in self.PLANES_ITEMS_COLORS:
			shaded_color = [v / 255.0 for v in shaded_color]
			wire_color = [v / 255.0 for v in wire_color]

			normal_colors.append((tuple(shaded_color), tuple(wire_color)))

		self.PLANES_ITEMS_COLORS = tuple(normal_colors)
		self.__build_render_items_specs()

	def __build_render_items_specs(self):
		self._render_items_specs = []
		depth_priority = 0.0

		# Create planes' render items shaders
		for item_name, item_colors in zip(self.PLANES_NAMES, self.PLANES_ITEMS_COLORS):
			shaded_color, wire_color = item_colors
			shaded_color = om.MColor(shaded_color)
			wire_color = om.MColor(wire_color)

			shaded_color.a = 0.75
			wire_color.a = 1.0

			plane_shader = omr.MRenderer.getShaderManager().getStockShader(omr.MShaderManager.k3dSolidShader)
			plane_wire_shader = omr.MRenderer.getShaderManager().getStockShader(omr.MShaderManager.k3dThickLineShader)
			# plane_wire_shader = omr.MRenderer.getShaderManager().getStockShader(omr.MShaderManager.k3dFatPointShader)

			# Set the shaders' parameters
			plane_shader.setParameter('solidColor', shaded_color)
			plane_shader.setParameter('DepthPriority', depth_priority)
			plane_shader.setIsTransparent(True)

			plane_wire_shader.setParameter('solidColor', wire_color)
			plane_wire_shader.setParameter('lineWidth', (2.0, 2.0))
			plane_wire_shader.setParameter('DepthPriority', depth_priority)

			shaded_spec = RenderItemSpec(item_name,
			                             omr.MGeometry.kTriangles,
			                             omr.MGeometry.kShaded,
			                             plane_shader)
			wire_spec = RenderItemSpec("{}Wire".format(item_name),
			                           omr.MGeometry.kLines,
			                           omr.MGeometry.kWireframe,
			                           plane_wire_shader)

			self._render_items_specs.append(shaded_spec)
			self._render_items_specs.append(wire_spec)

		print(">> Total render items: {}".format(len(self._render_items_specs)))

	@staticmethod
	def creator(obj):
		return SpaceVisGeometryOverride(obj)

	def supportedDrawAPIs(self):
		# Supports GL and DX
		return self._draw_apis

	def hasUIDrawables(self):
		return False

	def updateDG(self):
		mfn_dep_node = om.MFnDependencyNode(self._obj)
		planes_scale_plug = mfn_dep_node.findPlug(SpaceVis.PLANES_SCALE_SPECS.short, False)
		origin_offset_plug = mfn_dep_node.findPlug(SpaceVis.ORIGIN_OFFSET_BLEND_SPECS.short, False)
		origin_offset_matrix = om.MFnMatrixData(
			mfn_dep_node.findPlug(SpaceVis.ORIGIN_OFFSET_MATRIX_SPECS.short, False).asMObject()
		).matrix().inverse()
		xy_base1_plug = mfn_dep_node.findPlug(SpaceVis.PLANE_XY_BASE1_SPECS.short, False)
		xy_base2_plug = mfn_dep_node.findPlug(SpaceVis.PLANE_XY_BASE2_SPECS.short, False)
		xz_base1_plug = mfn_dep_node.findPlug(SpaceVis.PLANE_XZ_BASE1_SPECS.short, False)
		xz_base2_plug = mfn_dep_node.findPlug(SpaceVis.PLANE_XZ_BASE2_SPECS.short, False)
		yz_base1_plug = mfn_dep_node.findPlug(SpaceVis.PLANE_YZ_BASE1_SPECS.short, False)
		yz_base2_plug = mfn_dep_node.findPlug(SpaceVis.PLANE_YZ_BASE2_SPECS.short, False)

		planes_scale = planes_scale_plug.asShort()
		xy_base1 = (xy_base1_plug.child(0).asFloat(), xy_base1_plug.child(1).asFloat(), xy_base1_plug.child(2).asFloat())
		xy_base2 = (xy_base2_plug.child(0).asFloat(), xy_base2_plug.child(1).asFloat(), xy_base2_plug.child(2).asFloat())
		xz_base1 = (xz_base1_plug.child(0).asFloat(), xz_base1_plug.child(1).asFloat(), xz_base1_plug.child(2).asFloat())
		xz_base2 = (xz_base2_plug.child(0).asFloat(), xz_base2_plug.child(1).asFloat(), xz_base2_plug.child(2).asFloat())
		yz_base1 = (yz_base1_plug.child(0).asFloat(), yz_base1_plug.child(1).asFloat(), yz_base1_plug.child(2).asFloat())
		yz_base2 = (yz_base2_plug.child(0).asFloat(), yz_base2_plug.child(1).asFloat(), yz_base2_plug.child(2).asFloat())

		if (planes_scale != self.planes_scale or
		        xy_base1 != self.xy_bases[0] or
		        xy_base2 != self.xy_bases[1] or
		        xz_base1 != self.xz_bases[0] or
		        xz_base2 != self.xz_bases[1] or
		        yz_base1 != self.yz_bases[0] or
		        yz_base2 != self.yz_bases[1]):
			# Planes' scales changed. This means new points were created
			print(">> >> Planes' scale or bases changed")
			planes_bases = [(xy_base1, xy_base2),
			                (xz_base1, xz_base2),
			                (yz_base1, yz_base2)]
			self.vtx_points_backup, self.vtx_normals_vectors = space_vis_points(planes_scale, planes_bases=planes_bases)
			self.vtx_points = [point for point in self.vtx_points_backup]
			self.xy_bases, self.xz_bases, self.yz_bases = planes_bases

			# The number of points has changed. Therefore, the geos' ids have to be updated
			if planes_scale != self.planes_scale:
				self.lines_points_ids, self.tri_points_ids = space_vis_geo_sets(*get_rows_cols_count(len(self.vtx_points)))

			self.planes_scale = planes_scale
			self._stream_dirty = True

		origin_offset_blend = origin_offset_plug.asDouble()
		if (origin_offset_blend != self.origin_offset_blend or
					self.origin_offset_matrix != origin_offset_matrix or
					self._stream_dirty):
			print(">> >> Origin offset blend or matrix changed")
			# Space offset changed. This means points have changed but remain the same total number
			parent_trans_inv_matrix = om.MTransformationMatrix(origin_offset_matrix)
			parent_inv_pos_vector = parent_trans_inv_matrix.translation(om.MSpace.kWorld)
			parent_inv_pos_scaled_vector = parent_inv_pos_vector * (1.0 - origin_offset_blend)

			# Scale the parent inverse position vector
			parent_w_inv_pos = (parent_inv_pos_scaled_vector.x,
			                    parent_inv_pos_scaled_vector.y,
			                    parent_inv_pos_scaled_vector.z)

			self.vtx_points = [vector_add((point, parent_w_inv_pos)) for point in self.vtx_points_backup]
			self.origin_offset_matrix = origin_offset_matrix
			self.origin_offset_blend = origin_offset_blend
			self._stream_dirty = True

	def cleanUp(self):
		pass

	def isIndexingDirty(self, item):
		return True

	def isStreamDirty(self, desc):
		return self._stream_dirty

	def hasUIDrawables(self):
		return True

	def updateRenderItems(self, dag_path, render_list):
		print(">> From updateRenderItems...")
		for spec in self._render_items_specs:
			# Make sure the render item already exists and is inside the list of render items received as argument
			index = render_list.indexOf(spec.name)
			if index > -1:
				print(">> Found render item {}".format(spec.name))
				render_item = render_list[index]
			else:
				# The render item was not found. Therefore, create it and append it to the list received as argument
				print(">> Creating render item {}".format(spec.name))
				render_item = omr.MRenderItem.create(spec.name, omr.MRenderItem.DecorationItem, spec.geo_type)
				render_item.setDrawMode(spec.draw_mode)
				render_item.setDepthPriority(5)
				render_list.append(render_item)

			render_item.setShader(spec.shader)
			render_item.enable(True)

	def populateGeometry(self, requirements, render_items, data):
		print(">> From populate geometry...")
		vtx_buffer_descriptor_list = requirements.vertexRequirements()

		for vtx_buffer_descriptor in vtx_buffer_descriptor_list:
			# The normals and vertices lists contain the same number of elements
			vtx_vectors_count = len(self.vtx_points)
			vts_buffer = data.createVertexBuffer(vtx_buffer_descriptor)
			vts_data_addr = vts_buffer.acquire(vtx_vectors_count, True)
			vts_data = ((ctypes.c_float * 3) * vtx_vectors_count).from_address(vts_data_addr)

			if vtx_buffer_descriptor.semantic == omr.MGeometry.kPosition:
				for i, point in enumerate(self.vtx_points):
					for j, coord in enumerate(point):
						vts_data[i][j] = coord
			elif vtx_buffer_descriptor.semantic == omr.MGeometry.kNormal:
				for i, normal in enumerate(self.vtx_normals_vectors):
					for j, coord in enumerate(normal):
						vts_data[i][j] = coord
			else:
				continue
			print(">> Committing {} buffer".format(
				"vertices" if vtx_buffer_descriptor.semantic == omr.MGeometry.kPosition else "normals"))
			vts_buffer.commit(vts_data_addr)

		# Create an index buffer for each render item received as argument
		for item in render_items:
			if not item:
				continue

			for plane_index, plane_name in enumerate(self.PLANES_NAMES):
				if item.name().startswith(plane_name):
					print(">> Setting buffer for {}".format(plane_name))
					if item.name().lower().find("wire") < 0:
						points_ids = self.tri_points_ids[plane_index]
					else:
						points_ids = [point for line_points in self.lines_points_ids[plane_index] for point in
						              line_points]
						# Draw points,instead
						# points_ids = [i for i in range(len(self.vtx_points))]
					break
			else:
				# The render item was not found in the list of names
				continue

			indices_count = len(points_ids)
			index_buffer = data.createIndexBuffer(omr.MGeometry.kUnsignedInt32)
			indices_address = index_buffer.acquire(indices_count, True)
			indices = (ctypes.c_uint * indices_count).from_address(indices_address)
			for i, point_id in enumerate(points_ids):
				indices[i] = point_id

			index_buffer.commit(indices_address)
			item.associateWithIndexBuffer(index_buffer)

		self._stream_dirty = False

	def addUIDrawables(self, path, draw_manager, frame_context):
		draw_manager.beginDrawable()

		text_position = om.MPoint(5.0, 5.0, 5.0)
		text = "Test message"
		text_align = draw_manager.kRight
		is_dynamic = True

		draw_manager.text(text_position, text, alignment=text_align, dynamic=is_dynamic)

		draw_manager.endDrawable()

		return self


def initializePlugin(obj):
	plugin = om.MFnPlugin(obj, "Rafael Valenzuela Ochoa", "1.0", "HuevoCartoon")
	try:
		plugin.registerNode(
			"spaceVis",
			SpaceVis.typeId,
			SpaceVis.creator,
			SpaceVis.initialize,
			om.MPxNode.kLocatorNode,
			SpaceVis.drawDBClassification
		)
	except RuntimeError as re:
		sys.stderr.write("Failed to register node SpaceVis.")
		raise re

	# Register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.registerGeometryOverrideCreator(
			SpaceVis.drawDBClassification,
			SpaceVis.drawRegistrantId,
			SpaceVisGeometryOverride.creator
		)
	except:
		sys.stderr.write("Failed to register override for node SpaceVis")
		raise

	try:
		om.MSelectionMask.registerSelectionType("spaceVisSelection")
		mel.eval("selectType -byName \"spaceVisSelection\" 1")
	except:
		sys.stderr.write("Failed to register selection mask\n")
		raise


def uninitializePlugin(obj):
	plugin = om.MFnPlugin(obj)
	try:
		plugin.deregisterNode(SpaceVis.typeId)
	except RuntimeError as re:
		sys.stderr.write("Failed to de-register node SpaceVis")
		pass

	# De-register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.deregisterGeometryOverrideCreator(
			SpaceVis.drawDBClassification,
			SpaceVis.drawRegistrantId
		)
	except:
		sys.stderr.write("Failed to de-register override for node SpaceVis")
		pass

	try:
		om.MSelectionMask.deregisterSelectionType("spaceVisSelection")
	except:
		sys.stderr.write("Failed to de-register selection mask\n")
		pass
