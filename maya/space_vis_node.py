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

	for plane_index, bases in enumerate(planes_bases):
		normal = bases[2]
		plane_off = rows_count * cols_count * plane_index
		for i in [(r * rows_count) + c + plane_off for r in range(0, rows_count - 1, 1) for c in range(0, cols_count - 1, 1)]:
			tri_points.append(vtx_points[i])
			tri_points.append(vtx_points[i + 1])
			tri_points.append(vtx_points[i + cols_count])
			tri_points.append(vtx_points[i + cols_count])
			tri_points.append(vtx_points[i + cols_count + 1])
			tri_points.append(vtx_points[i + 1])

			for __ in range(6):
				vtx_normals.append(normal)

	return vtx_points, tri_points, vtx_normals


class SpaceVis(omui.MPxLocatorNode):
	kPluginNodeId = om.MTypeId(0x80006)
	drawDBClassification = "drawdb/geometry/spaceVis"
	drawRegistrantId = "SpaceVisPlugin"
	typeId = om.MTypeId(0x80006)

	def __init__(self):
		super(SpaceVis, self).__init__()

	@classmethod
	def creator(cls):
		return cls()

	@staticmethod
	def initialize():
		pass

	def default_bounding_box(self):
		return om.MBoundingBox()

	def compute(self, plug, data_block):
		"""

		:param plug: OpenMaya.MPlug instance
		:param data_block: OpenMaya.MDataBlock instance
		"""
		pass

	def draw(self, view, path, style, status):
		vtx_points, tri_points, __ = space_vis_vertices_pos()[0]
		rows_count = 5
		cols_count = 5

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

		# Set the bind\'s line color to solid blue
		gl_ft.glColor4f(0.0, 0.0, 255.0, 255.0)
		# Enable transparency
		gl_ft.glEnable(v1omr.MGL_BLEND)

		# Start drawing the bind\'s lines
		gl_ft.glBegin(v1omr.MGL_LINES)
		for row_index in range(rows_count):
			for col_index in range(1, cols_count, 1):
				col_index = (row_index * rows_count) + col_index
				start_point = vtx_points[col_index - 1]
				end_point = vtx_points[col_index]
				gl_ft.glVertex3f(*start_point)
				gl_ft.glVertex3f(*end_point)

		# End drawing the bind\'s lines
		gl_ft.glEnd()

		# Start drawing the bind\'s triangle faces
		# Push the color settings
		gl_ft.glPushAttrib(v1omr.MGL_CURRENT_BIT)

		# Show both faces
		gl_ft.glDisable(v1omr.MGL_CULL_FACE)

		view.setDrawColor(13, omui.M3dView.kActiveColors)

		gl_ft.glBegin(v1omr.MGL_TRIANGLE_FAN)

		for i in range(0, len(tri_points), 3):
			gl_ft.glVertex3f(tri_points[i], tri_points[i + 1], tri_points[i + 2])

		gl_ft.glEnd()

		gl_ft.glPopAttrib()
		# End drawing the bind\'s triangle faces

		# Disable transparency
		gl_ft.glDisable(v1omr.MGL_BLEND)

		view.endGL()

	def isBounded(self):
		return True

	def boundingBox(self):
		bbox = om.MBoundingBox(self.default_bounding_box())
		return bbox


#######################################################################################################################
#
#  Viewport 2.0 override implementation
#
#######################################################################################################################

class SpaceVisGeometryOverride(omr.MPxGeometryOverride):
	vtx_vectors = None
	vtx_normals_vectors = None
	_render_items = None

	PLANES_ITEMS_NAMES = ["yzPlane", "xzPlane", "xyPlane"]
	PLANES_ITEMS_COLORS = [
		(om.MColor([0.6, 0.02, 0.08]), om.MColor([0.7, 0.0, 0.1])),
		(om.MColor([0.2, 1.0, 0.1]), om.MColor([0.1, 0.7, 0.0])),
		(om.MColor([0.1, 0.2, 1.0]), om.MColor([0.0, 0.1, 0.7]))
	]

	def __init__(self, obj):
		super(SpaceVisGeometryOverride, self).__init__(obj)
		vtx_points, tri_points, vtx_normals = space_vis_vertices_pos()
		self.vtx_vectors = [om.MVector(*point) for point in vtx_points]
		self.tri_vectors = [om.MVector(*point) for point in tri_points]
		self.vtx_normals_vectors = [om.MVector(*normal) for normal in vtx_normals]

		# Create planes' render items shaders
		for item_name, item_colors in zip(self.PLANES_ITEMS_NAMES, self.PLANES_ITEMS_COLORS):
			shaded_color, wire_color = item_colors
			plane_shader = omr.MRenderer.getShaderManager().getStockShader(omr.MShaderManager.k3dBlinnShader)
			plane_shader.setParameter('diffuseColor', shaded_color)

			self._render_items.append((item_name, omr.MGeometry.kTriangles, omr.MGeometry.kShaded, plane_shader))
			self._render_items.append(("{}Wire".format(item_name), omr.MGeometry.kTriangles,
			                           omr.MGeometry.kWireframe, plane_shader))

	def supportedDrawAPIs(self):
		# Supports GL and DX
		return omr.MRenderer.kOpenGL | omr.MRenderer.kOpenGLCoreProfile | omr.MRenderer.kDirectX11

	def hasUIDrawables(self):
		return False

	def populateGeometry(self, requirements, render_items, data):
		vtx_buffer_descriptor_list = requirements.vertexRequirements()

		for vtx_buffer_descriptor in vtx_buffer_descriptor_list:
			vtx_vectors_count = len(self.tri_vectors)

			if vtx_buffer_descriptor.semantic == omr.MGeometry.kPosition:
				vts_buffer = data.createVertexBuffer(vtx_buffer_descriptor)
				vts_position_data_addr = vts_buffer.acquire(vtx_vectors_count, True)
				vts_position_data = ((ctypes.c_float * 3) * vtx_vectors_count).from_address(vts_position_data_addr)
				for i in range(vtx_vectors_count):
					pos = self.tri_vectors[i]
					for j in range(len(pos)):
						vts_position_data[i][j] = pos[j]
				vts_buffer.commit(vts_position_data_addr)
			elif vtx_buffer_descriptor.semantic == omr.MGeometry.kNormal:
				vts_normal_buffer = data.createVertexBuffer(vtx_buffer_descriptor)
				vts_normal_data_addr = vts_normal_buffer.acquire(vtx_vectors_count, True)
				vts_normal_data = ((ctypes.c_float * 3) * vtx_vectors_count).from_address(vts_normal_data_addr)

				for i in range(vtx_vectors_count):
					normal = self.vtx_normals_vectors[i]
					for j in range(len(normal)):
						vts_normal_data[i][j] = normal[j]
				vts_normal_buffer.commit(vts_normal_data_addr)
			else:
				pass

		for item in render_items:
			if not item:
				continue

			index_buffer = data.createIndexBuffer(omr.MGeometry.kUnsignedInt32)
			if item.name().startswith(self.PLANES_ITEMS_NAMES[0]):
				plane_points_start = 0
				plane_points_end = 96    # Each plane has 96 triangle points (16 * 6)
			elif item.name().startswith(self.PLANES_ITEMS_NAMES[1]):
				plane_points_start = 96
				plane_points_end = 96 * 2
			else:
				plane_points_start = 96 * 2
				plane_points_end = 96 * 3

			plane_shape_vectors = self.tri_vectors[plane_points_start:plane_points_end]
			plane_tri_vectors_count = len(plane_shape_vectors)
			indices_address = index_buffer.acquire(plane_tri_vectors_count, True)
			indices = (ctypes.c_uint * plane_tri_vectors_count).from_address(indices_address)
			for i in range(plane_tri_vectors_count):
				indices[i] = i
			index_buffer.commit(indices_address)
			item.associateWithIndexBuffer(index_buffer)


def initializePlugin(obj):
	plugin = om.MFnPlugin(obj, "Rafael Valenzuela Ochoa", "1.0", "HuevoCartoon")
	try:
		plugin.registerNode(
			"transformControl",
			SpaceVis.typeId,
			SpaceVis.creator,
			SpaceVis.initialize,
			om.MPxNode.kLocatorNode,
			SpaceVis.drawDBClassification
		)
	except RuntimeError as re:
		sys.stderr.write( "Failed to register node TransformControlLocator." )
		raise re

	# Register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.registerGeometryOverrideCreator(
			SpaceVis.drawDBClassification,
			SpaceVis.drawRegistrantId,
			SpaceVisGeometryOverride.creator
		)
	except:
		sys.stderr.write("Failed to register override for node TransformControlLocator")
		raise

	try:
		om.MSelectionMask.registerSelectionType("transformControlSelection")
		mel.eval("selectType -byName \"transformControlSelection\" 1")
	except:
		sys.stderr.write("Failed to register selection mask\n")
		raise


def uninitializePlugin(obj):
	plugin = om.MFnPlugin(obj)
	try:
		plugin.deregisterNode(SpaceVis.typeId)
	except RuntimeError as re:
		sys.stderr.write("Failed to deregister node TransformControlLocator")
		pass

	# De-register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.deregisterGeometryOverrideCreator(
			SpaceVis.drawDBClassification,
			SpaceVis.drawRegistrantId
		)
	except:
		sys.stderr.write("Failed to deregister override for node TransformControlLocator")
		pass

	try:
		om.MSelectionMask.deregisterSelectionType("transformControlSelection")
	except:
		sys.stderr.write("Failed to deregister selection mask\n")
		pass
