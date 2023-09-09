import sys
import ctypes
from collections import namedtuple

import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

maya_useNewAPI = True


def space_vis_vertices_pos(range_scale=2):
	min_lines = 1
	lines_per_side = min_lines * range_scale
	rows_count = cols_count = (lines_per_side * 2) + 1
	vtx_points = []
	vtx_normals = []
	tri_points = []
	lines_points = []
	planes_bases = [
		((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
		((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
		((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
	]

	for base_a, base_b, normal in planes_bases:
		# Calculate the points from positive to negative in both directions: vertically and horizontally
		for j in range(lines_per_side, lines_per_side - rows_count, -1):
			base_b_scaled = [c * j for c in base_b]
			for i in range(lines_per_side * -1, cols_count - lines_per_side, 1):
				vtx_points.append([(co * i) + base_b_scaled[co_i] for co_i, co in enumerate(base_a)])
				# Save a copy of the normal for the plane for each calculated point
				vtx_normals.append(normal)

	for plane_index, bases in enumerate(planes_bases):
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

	return vtx_points, lines_points, tri_points, vtx_normals


class SpaceVis(omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/spaceVis"
	drawRegistrantId = "SpaceVisPlugin"
	typeId = om.MTypeId(0x80006)

	PLANES_SCALE_ATTR_NAMES = ("planesScale", "planesScale")
	planes_scale_attr = None

	def __init__(self):
		super(SpaceVis, self).__init__()
		self.planes_colors = [
			(0.0, 0.0, 255.0, 255.0),
			(0.0, 255.0, 0.0, 255.0),
			(255.0, 0.0, 0.0, 255.0)
		]
		vtx_points, lines_points_ids, tri_points_ids, vtx_normals = space_vis_vertices_pos(3)
		self.vtx_points = vtx_points
		self.lines_points_ids = lines_points_ids
		self.tri_points_ids = tri_points_ids
		self.plane_tris_count = len(tri_points_ids[0])
		self.vtx_normals_vectors = vtx_normals

	@classmethod
	def creator(cls):
		return cls()

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		short_name, long_name = SpaceVis.PLANES_SCALE_ATTR_NAMES
		SpaceVis.planes_scale_attr = mfn_num_attr.create(short_name, long_name, om.MFnNumericData.kShort)
		mfn_num_attr.keyable = True
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.default = 1.0

		SpaceVis.addAttribute(SpaceVis.planes_scale_attr)

	def compute(self, plug, data_block):
		"""

		:param plug: OpenMaya.MPlug instance
		:param data_block: OpenMaya.MDataBlock instance
		"""

		if plug.attribute() == self.planes_scale_attr:
			print(">> Updating the planes' scale")
			planes_scale = data_block.inputValue()
			self.vtx_points, self.lines_points_ids, self.tri_points_ids, self.vtx_normals_vectors = space_vis_vertices_pos(planes_scale)

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

		for plane_points_ids, plane_color in zip(self.lines_points_ids, self.planes_colors):
			# Set the planes' line color accordingly
			gl_ft.glColor4f(*plane_color)

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

		for plane_points_ids, plane_color in zip(self.tri_points_ids, self.planes_colors):
			# Set the planes' line color accordingly
			plane_color_cp = [v for v in plane_color]
			plane_color_cp[-1] = 100.0

			gl_ft.glColor4f(*plane_color_cp)

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


class SpaceVisGeometryOverride(omr.MPxGeometryOverride):
	vtx_points = None
	lines_points_ids = None
	tri_points_ids = None
	vtx_normals_vectors = None
	plane_tris_count = None

	_obj = None
	_render_items_specs = None
	_stream_dirty = False
	_draw_apis = omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile | omr.MRenderer.kDirectX11

	PLANES_ITEMS_NAMES = ["yzPlane", "xzPlane", "xyPlane"]
	PLANES_ITEMS_COLORS = [
		(om.MColor([0.6, 0.02, 0.08]), om.MColor([0.7, 0.0, 0.1])),
		(om.MColor([0.2, 1.0, 0.1]), om.MColor([0.1, 0.7, 0.0])),
		(om.MColor([0.1, 0.2, 1.0]), om.MColor([0.0, 0.1, 0.7]))
	]

	def __init__(self, obj):
		super(SpaceVisGeometryOverride, self).__init__(obj)

		self._render_items_specs = []
		self._obj = obj

		self.set_geometry_lists(*space_vis_vertices_pos())
		self.__build_render_items_specs()

		print(">> Points: {}".format(len(self.vtx_points)))
		print(">> Tris: {}".format(len(self.tri_points_ids)))
		print(">> Normals: {}".format(len(self.vtx_normals_vectors)))

	def __build_render_items_specs(self):
		self._render_items_specs = []
		depth_priority = 0.0

		# Create planes' render items shaders
		for item_name, item_colors in zip(self.PLANES_ITEMS_NAMES, self.PLANES_ITEMS_COLORS):
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

	def set_geometry_lists(self, vtx_points, lines_points_ids, tri_points_ids, vtx_normals):
		self.vtx_points = vtx_points
		self.lines_points_ids = lines_points_ids
		self.tri_points_ids = tri_points_ids
		self.plane_tris_count = len(tri_points_ids[0])
		self.vtx_normals_vectors = vtx_normals

	def supportedDrawAPIs(self):
		# Supports GL and DX
		return self._draw_apis

	def hasUIDrawables(self):
		return False

	def updateDG(self):
		planes_scale_plug = om.MFnDependencyNode(self._obj).findPlug(SpaceVis.PLANES_SCALE_ATTR_NAMES[0], False)
		if not planes_scale_plug or planes_scale_plug.isNull:
			self._stream_dirty = False
			return

		planes_scale = planes_scale_plug.asShort()
		self.set_geometry_lists(*space_vis_vertices_pos(planes_scale))
		self._stream_dirty = True

	def cleanUp(self):
		pass

	def isIndexingDirty(self, item):
		return True

	def isStreamDirty(self, desc):
		return self._stream_dirty

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
			print(">> Committing {} buffer".format("vertices" if vtx_buffer_descriptor.semantic == omr.MGeometry.kPosition else "normals"))
			vts_buffer.commit(vts_data_addr)

		# Create an index buffer for each render item received as argument
		for item in render_items:
			if not item:
				continue

			for plane_index, plane_name in enumerate(self.PLANES_ITEMS_NAMES):
				if item.name().startswith(plane_name):
					print(">> Setting buffer for {}".format(plane_name))
					if item.name().lower().find("wire") > -1:
						points_ids = [point for line_points in self.lines_points_ids[plane_index] for point in line_points]
						# Draw points,instead
						#points_ids = [i for i in range(len(self.vtx_points))]
						indices_count = len(points_ids)
					else:
						indices_count = self.plane_tris_count
						points_ids = self.tri_points_ids[plane_index]
					break
			else:
				# The render item was not found in the list of names
				continue

			index_buffer = data.createIndexBuffer(omr.MGeometry.kUnsignedInt32)
			indices_address = index_buffer.acquire(indices_count, True)
			indices = (ctypes.c_uint * indices_count).from_address(indices_address)
			for i, point_id in enumerate(points_ids):
				indices[i] = point_id

			index_buffer.commit(indices_address)
			item.associateWithIndexBuffer(index_buffer)

		self._stream_dirty = False


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
