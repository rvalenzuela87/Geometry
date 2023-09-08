import sys
import ctypes

import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

maya_useNewAPI = True


def space_vis_vertices_pos():
	rows_count = 5
	cols_count = 5
	vtx_points = []
	vtx_normals = []
	tri_points = []
	planes_bases = [
		((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
		((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
		((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
	]

	for base_a, base_b, normal in planes_bases:
		for j in range(2, -3, -1):
			base_b_scaled = [c * j for c in base_b]
			for i in range(-2, 3, 1):
				vtx_points.append([(co * i) + base_b_scaled[co_i] for co_i, co in enumerate(base_a)])

	lines_points = []

	for plane_index, bases in enumerate(planes_bases):
		normal = bases[2]
		plane_off = rows_count * cols_count * plane_index
		plane_tri_points = [
			plane_off,
			plane_off + cols_count - 1,
			plane_off + (rows_count * (cols_count - 1)),
			plane_off + (rows_count * cols_count) - 1,
			plane_off + cols_count - 1
		]
		plane_lines_points = []
		for i in range(plane_off, plane_off + (rows_count * cols_count), cols_count):
			plane_lines_points.append((i, i + cols_count - 1))

		for i in range(plane_off, plane_off + cols_count, 1):
			plane_lines_points.append((i, i + rows_count * (cols_count - 1)))

		tri_points.append(plane_tri_points)
		lines_points.append(plane_lines_points)
		vtx_normals.append([normal for __ in range(len(plane_tri_points))])

	return vtx_points, lines_points, tri_points, vtx_normals


class SpaceVis(omui.MPxLocatorNode):
	kPluginNodeId = om.MTypeId(0x80006)
	drawDBClassification = "drawdb/geometry/spaceVis"
	drawRegistrantId = "SpaceVisPlugin"
	typeId = om.MTypeId(0x80006)

	planes_scale_attr = None

	def __init__(self):
		super(SpaceVis, self).__init__()
		self.planes_colors = [
			(0.0, 0.0, 255.0, 255.0),
			(0.0, 255.0, 0.0, 255.0),
			(255.0, 0.0, 0.0, 255.0)
		]

	@classmethod
	def creator(cls):
		return cls()

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		SpaceVis.planes_scale_attr = mfn_num_attr.create("planesScale", "planesScale", om.MFnNumericData.kDouble)
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

		data_block.setClean(plug)

	def draw(self, view, path, style, status):
		vtx_points, lines_points_ids, tri_points_ids, __ = space_vis_vertices_pos()

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

		for plane_points_ids, plane_color in zip(lines_points_ids, self.planes_colors):
			# Set the planes' line color accordingly
			gl_ft.glColor4f(*plane_color)

			for start_id, end_id in plane_points_ids:
				gl_ft.glVertex3f(*vtx_points[start_id])
				gl_ft.glVertex3f(*vtx_points[end_id])

		# End drawing the planes' lines
		gl_ft.glEnd()

		# Start drawing the planes' triangle faces
		# Push the color settings
		gl_ft.glPushAttrib(v1omr.MGL_CURRENT_BIT)

		# Show both faces
		gl_ft.glDisable(v1omr.MGL_CULL_FACE)

		view.setDrawColor(13, omui.M3dView.kActiveColors)

		for plane_points_ids, plane_color in zip(tri_points_ids, self.planes_colors):
			# Set the planes' line color accordingly
			plane_color_cp = [v for v in plane_color]
			plane_color_cp[-1] = 100.0

			gl_ft.glColor4f(*plane_color_cp)

			gl_ft.glBegin(v1omr.MGL_TRIANGLE_FAN)

			for point_id in plane_points_ids:
				gl_ft.glVertex3f(*vtx_points[point_id])

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

class SpaceVisData(om.MUserData):
	def __init__(self):
		# The boolean argument tells Maya to don\'t delete the data after draw
		super(SpaceVisData, self).__init__(False)


class SpaceVisGeometryOverride(omr.MPxGeometryOverride):
	vtx_points = None
	vtx_normals_vectors = None
	_obj = None
	_render_items = None
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

		vtx_points, lines_points_ids, tri_points_ids, vtx_normals = space_vis_vertices_pos()
		self.vtx_points = vtx_points
		self.tri_points_ids = tri_points_ids
		self.lines_points_ids = lines_points_ids
		self.plane_tris_count = len(tri_points_ids[0])
		self.vtx_normals_vectors = vtx_normals

		self._render_items = []
		self._obj = obj

		print(">> Points: {}".format(len(self.vtx_points)))
		print(">> Tris: {}".format(len(self.tri_points_ids)))
		print(">> Normals: {}".format(len(self.vtx_normals_vectors)))

		# Create planes' render items shaders
		for item_name, item_colors in zip(self.PLANES_ITEMS_NAMES, self.PLANES_ITEMS_COLORS):
			shaded_color, wire_color = item_colors
			plane_shader = omr.MRenderer.getShaderManager().getStockShader(omr.MShaderManager.k3dBlinnShader)
			plane_shader.setParameter('diffuseColor', shaded_color)

			self._render_items.append((item_name, omr.MGeometry.kTriangles, omr.MGeometry.kShaded, plane_shader))
			self._render_items.append(("{}Wire".format(item_name), omr.MGeometry.kTriangles,
			                           omr.MGeometry.kWireframe, plane_shader))
		print(">> Total render items: {}".format(len(self._render_items)))

	@staticmethod
	def creator(obj):
		return SpaceVisGeometryOverride(obj)

	def supportedDrawAPIs(self):
		# Supports GL and DX
		return self._draw_apis

	def hasUIDrawables(self):
		return False

	def updateDG(self):
		self._stream_dirty = True

	def cleanUp(self):
		pass

	def isIndexingDirty(self, item):
		return True

	def isStreamDirty(self):
		return self._stream_dirty

	def updateRenderItems(self, dag_path, render_list):
		print(">> From updateRenderItems...")
		for item_name, geo_type, draw_mode, shader in self._render_items:
			index = render_list.indexOf(item_name)
			if index < 0:
				print(">> Creating render item {}".format(item_name))
				render_item = omr.MRenderItem.create(item_name, omr.MRenderItem.DecorationItem, geo_type)
				render_item.setDrawMode(draw_mode)
				render_item.setDepthPriority(5)
				render_list.append(render_item)
			else:
				print(">> Found render item {}".format(item_name))
				render_item = render_list[index]

			render_item.setShader(shader)
			render_item.enable(True)

	def populateGeometry(self, requirements, render_items, data):
		print(">> From populate geometry...")
		vtx_buffer_descriptor_list = requirements.vertexRequirements()
		# Flatten the planes' triangles and normals lists
		vtx_points = [self.vtx_points[point_id] for plane_points_ids in self.tri_points_ids
		              for point_id in plane_points_ids]
		vtx_normals = [normal for plane_normals in self.vtx_normals_vectors for normal in plane_normals]

		for vtx_buffer_descriptor in vtx_buffer_descriptor_list:
			vtx_vectors_count = len(vtx_points)
			vts_buffer = data.createVertexBuffer(vtx_buffer_descriptor)
			vts_data_addr = vts_buffer.acquire(vtx_vectors_count, True)
			vts_data = ((ctypes.c_float * 3) * vtx_vectors_count).from_address(vts_data_addr)

			if vtx_buffer_descriptor.semantic == omr.MGeometry.kPosition:
				for i in range(vtx_vectors_count):
					pos = vtx_points[i]
					print(pos)
					for j in range(len(pos)):
						vts_data[i][j] = pos[j]
			elif vtx_buffer_descriptor.semantic == omr.MGeometry.kNormal:
				for i in range(vtx_vectors_count):
					normal = vtx_normals[i]
					for j in range(len(normal)):
						vts_data[i][j] = normal[j]
			else:
				continue
			print(">> Committing {} buffer".format("vertices" if vtx_buffer_descriptor.semantic == omr.MGeometry.kPosition else "normals"))
			vts_buffer.commit(vts_data_addr)

		for item in render_items:
			if not item:
				continue

			for plane_index, plane_name in enumerate(self.PLANES_ITEMS_NAMES):
				if item.name().startswith(plane_name):
					print(">> Setting buffer for {}".format(plane_name))
					plane_points_start = plane_index * self.plane_tris_count
					break
			else:
				continue

			index_buffer = data.createIndexBuffer(omr.MGeometry.kUnsignedInt32)
			indices_address = index_buffer.acquire(self.plane_tris_count, True)
			indices = (ctypes.c_uint * self.plane_tris_count).from_address(indices_address)
			for i in range(self.plane_tris_count):
				indices[i] = plane_points_start + i

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
