import sys
import math
from collections import namedtuple
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

maya_useNewAPI = True
DEFAULT_MASS = 1.0
DEFAULT_SPACE = om.MSpace.kObject


class CenterMassMixIn(object):
	def __init__(self, *args, **kwargs):
		super(CenterMassMixIn, self).__init__(*args, **kwargs)

	@staticmethod
	def get_points_from_shape(center_mass_vis_shape):
		mfn_dep_node = om.MFnDependencyNode(center_mass_vis_shape)
		mass_points_plug = mfn_dep_node.findPlug(CenterMassVis.mass_points_attr, False)

		for point_index in range(mass_points_plug.numElements()):
			mass_point_plug = mass_points_plug.elementByLogicalIndex(point_index)
			point_plug = mass_point_plug.child(0)
			point = om.MPoint(
				point_plug.child(0).asDouble(),
				point_plug.child(1).asDouble(),
				point_plug.child(2).asDouble(),
				mass_point_plug.child(1).asDouble()
			)

			yield point

	@staticmethod
	def calc_center_mass(points):
		center_vector = om.MVector()
		weight_sum = 0.0

		for point_index, point in enumerate(points):
			if point_index < 1:
				center_vector = om.MVector(point)
				weight_sum = point.w
				continue

			weight_sum += point.w
			point_vector = om.MVector(point)
			center_vector += (point_vector - center_vector) * (point.w/weight_sum)

		center_point = om.MPoint(center_vector.x, center_vector.y, center_vector.z, weight_sum)
		return center_point


class CenterMassVis(CenterMassMixIn, omui.MPxLocatorNode):
	drawDBClassification = "drawdb/geometry/centerOfMass"
	drawRegistrantId = "CenterMassVisPlugin"
	typeId = om.MTypeId(0x80007)

	show_mass_attr = None
	show_calc_attr = None
	mass_points_attr = None
	point_attr = None
	point_x_attr = None
	point_y_attr = None
	point_z_attr = None
	mass_attr = None
	center_mass_attr = None
	center_mass_x_attr = None
	center_mass_y_attr = None
	center_mass_z_attr = None
	mass_sum_attr = None
	mesh_attr = None
	curves_attr = None
	surfaces_attr = None

	def __init_(self):
		super(CenterMassVis, self).__init__()

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		mfn_comp_attr = om.MFnCompoundAttribute()
		mfn_enum_attr = om.MFnEnumAttribute()
		mfn_typed_attr = om.MFnTypedAttribute()

		CenterMassVis.show_mass_attr = mfn_enum_attr.create("massVis", "massVisibliity")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 1
		mfn_enum_attr.affectsAppearance = True

		CenterMassVis.show_calc_attr = mfn_enum_attr.create("calcVis", "calculationVisibility")
		mfn_enum_attr.addField("False", 0)
		mfn_enum_attr.addField("True", 1)
		mfn_enum_attr.writable = True
		mfn_enum_attr.storable = True
		mfn_enum_attr.keyable = False
		mfn_enum_attr.default = 0
		mfn_enum_attr.affectsAppearance = True

		CenterMassVis.point_attr = mfn_num_attr.createPoint("point", "point")
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.keyable = True
		mfn_num_attr.default = (0.0, 0.0, 0.0)
		mfn_num_attr.affectsAppearance = True

		CenterMassVis.point_x_attr = mfn_num_attr.child(0)
		CenterMassVis.point_y_attr = mfn_num_attr.child(1)
		CenterMassVis.point_z_attr = mfn_num_attr.child(2)

		CenterMassVis.mass_attr = mfn_num_attr.create("mass", "mass", om.MFnNumericData.kDouble)
		mfn_num_attr.storable = True
		mfn_num_attr.writable = True
		mfn_num_attr.keyable = True
		mfn_num_attr.default = DEFAULT_MASS
		mfn_num_attr.affectsAppearance = True

		CenterMassVis.mass_points_attr = mfn_comp_attr.create("inMassPoints", "inMassPoints")
		mfn_comp_attr.addChild(CenterMassVis.point_attr)
		mfn_comp_attr.addChild(CenterMassVis.mass_attr)
		mfn_comp_attr.array = True
		mfn_comp_attr.storable = True
		mfn_comp_attr.writable = True
		mfn_comp_attr.affectsAppearance = True

		CenterMassVis.mesh_attr = mfn_typed_attr.create("inMesh", "inMesh", om.MFnData.kMesh)
		mfn_typed_attr.array = True
		mfn_typed_attr.storable = False
		mfn_typed_attr.writable = True
		mfn_typed_attr.affectsAppearance = True

		CenterMassVis.curves_attr = mfn_typed_attr.create("inCurves", "inCurves", om.MFnData.kNurbsCurve)
		mfn_typed_attr.array = True
		mfn_typed_attr.storable = False
		mfn_typed_attr.writable = True
		mfn_typed_attr.affectsAppearance = True

		CenterMassVis.surfaces_attr = mfn_typed_attr.create("inSurface", "inSurface", om.MFnData.kNurbsSurface)
		mfn_typed_attr.array = True
		mfn_typed_attr.storable = False
		mfn_typed_attr.writable = True
		mfn_typed_attr.affectsAppearance = True

		# Output attributes

		CenterMassVis.center_mass_attr = mfn_num_attr.createPoint("centerOfMass", "centerOfMass")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (0.0, 0.0, 0.0)

		CenterMassVis.center_mass_x_attr = mfn_num_attr.child(0)
		CenterMassVis.center_mass_y_attr = mfn_num_attr.child(1)
		CenterMassVis.center_mass_z_attr = mfn_num_attr.child(2)

		CenterMassVis.mass_sum_attr = mfn_num_attr.create("massSum", "massSum", om.MFnNumericData.kDouble)
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = 0.0

		CenterMassVis.addAttribute(CenterMassVis.show_mass_attr)
		CenterMassVis.addAttribute(CenterMassVis.show_calc_attr)
		CenterMassVis.addAttribute(CenterMassVis.mass_points_attr)
		CenterMassVis.addAttribute(CenterMassVis.mesh_attr)
		CenterMassVis.addAttribute(CenterMassVis.curves_attr)
		CenterMassVis.addAttribute(CenterMassVis.surfaces_attr)
		CenterMassVis.addAttribute(CenterMassVis.center_mass_attr)
		CenterMassVis.addAttribute(CenterMassVis.mass_sum_attr)

		CenterMassVis.attributeAffects(CenterMassVis.point_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_x_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_y_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_z_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.mass_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.mesh_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.curves_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.surfaces_attr, CenterMassVis.center_mass_attr)

		CenterMassVis.attributeAffects(CenterMassVis.point_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_x_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_y_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_z_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.mass_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.mesh_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.curves_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.surfaces_attr, CenterMassVis.mass_sum_attr)

	def _it_mass_points_data_handle(self, array_data_handle):
		"""

		:param OpenMaya.MArrayDataHandle array_data_handle:
		:return:
		:rtype: iter(OpenMaya.MPoint,)
		"""
		while not array_data_handle.isDone():
			mass_point_data = array_data_handle.inputValue()
			point_plug = mass_point_data.child(self.point_attr)
			mass = mass_point_data.child(self.mass_attr).asDouble()

			mass_point = om.MPoint(
				point_plug.child(self.point_x_attr).asFloat(),
				point_plug.child(self.point_y_attr).asFloat(),
				point_plug.child(self.point_z_attr).asFloat(),
				mass
			)

			yield mass_point

			array_data_handle.next()

	@staticmethod
	def _it_mesh_data_handle(mesh_array_data_handle):
		"""

		:param OpenMaya.MArrayDataHandle mesh_array_data_handle:
		:return:
		:rtype: iter(OpenMaya.MPoint,)
		"""
		while not mesh_array_data_handle.isDone():
			mesh_data_handle = mesh_array_data_handle.inputValue()
			mesh_it = om.MItMeshVertex(mesh_data_handle.asMesh())
			while not mesh_it.isDone():
				vtx_point = mesh_it.position(DEFAULT_SPACE)
				vtx_point.w = DEFAULT_MASS

				yield vtx_point

				mesh_it.next()

			mesh_array_data_handle.next()

	@staticmethod
	def _it_surface_data_handle(surface_array_data_handle):
		"""

		:param OpenMaya.MArrayDataHandle surface_array_data_handle:
		:return:
		:rtype: iter(OpenMaya.MPoint,)
		"""
		while not surface_array_data_handle.isDone():
			surface_data_handle = surface_array_data_handle.inputValue()
			surface_cv_it = om.MItSurfaceCV(surface_data_handle.asNurbsSurface())
			while not surface_cv_it.isDone():
				cv_point = surface_cv_it.position(DEFAULT_SPACE)
				cv_point.w = DEFAULT_MASS

				yield cv_point

				surface_cv_it.next()

			surface_array_data_handle.next()

	@classmethod
	def creator(cls):
		return cls()

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
		mfn_dep_node = om.MFnDependencyNode(shape_path.node())
		show_mass = mfn_dep_node.findPlug(self.show_mass_attr, False).asBool()
		show_calc = mfn_dep_node.findPlug(self.show_calc_attr, False).asBool()

		# Drawing in VP1 views will be done using V1 Python APIs
		import maya.OpenMayaRender as v1omr

		gl_renderer = v1omr.MHardwareRenderer.theRenderer()
		gl_ft = gl_renderer.glFunctionTable()
		gl_ft.glPushAttrib(v1omr.MGL_CURRENT_BIT)

		# Start gl drawing
		view.beginGL()

		if show_mass:
			for point in self.get_points_from_shape(shape_path):
				view.drawText("{}".format(point.w), point)

		# Restore the state
		gl_ft.glPopAttrib()
		view.endGL()
		return self

	def compute(self, plug, data_block):
		"""

		:param OpenMaya.MPlug plug:
		:param OpenMaya.MDataBlock data_block:
		"""
		if plug.attribute() not in (self.center_mass_attr, self.center_mass_x_attr,
		                            self.center_mass_y_attr, self.center_mass_z_attr, self.mass_sum_attr):
			data_block.setClean(plug)
			return

		mesh_input_array = data_block.inputArrayValue(self.mesh_attr)
		surfaces_input_array = data_block.inputArrayValue(self.surfaces_attr)
		mass_points_input_array = data_block.inputArrayValue(self.mass_points_attr)

		mass_points_com = self.calc_center_mass(self._it_mass_points_data_handle(mass_points_input_array))
		mesh_com = self.calc_center_mass(self._it_mesh_data_handle(mesh_input_array))
		surface_com = self.calc_center_mass(self._it_surface_data_handle(surfaces_input_array))

		center_of_masses = []
		if mass_points_com.w > 0.0:
			center_of_masses.append(mass_points_com)

		if mesh_com.w > 0.0:
			center_of_masses.append(mesh_com)

		if surface_com.w > 0.0:
			center_of_masses.append(surface_com)

		center_mass = self.calc_center_mass(center_of_masses)

		center_mass_data = data_block.outputValue(self.center_mass_attr)
		mass_sum_data = data_block.outputValue(self.mass_sum_attr)

		center_mass_data.set3Float(center_mass.x, center_mass.y, center_mass.z)
		mass_sum_data.setDouble(center_mass.w)

		data_block.setClean(plug)


#######################################################################################################################
#
#  Viewport 2.0 override implementation
#
#######################################################################################################################


class CenterMassVisDrawUserData(om.MUserData):
	_delete_after_user = True
	mass_points = None
	show_mass = False

	def __init__(self):
		super(CenterMassVisDrawUserData, self).__init__()
		self.mass_points = []
		self.mesh_list = []
		self.surfaces_list = []
		self.curves_list = []
		self.show_mass = True

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


class CenterMassVisDrawOverride(CenterMassMixIn, omr.MPxDrawOverride):
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
		super(CenterMassVisDrawOverride, self).__init__(obj, callback, always_dirty)

		self._obj = obj
		self._in_vectors = []
		self._old_draw_data = None

	@staticmethod
	def creator(obj, *args, **kwargs):
		return CenterMassVisDrawOverride(obj, *args, **kwargs)

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
		:param CenterMassVisDrawUserData old_data:
		:return: The data to be passed to the draw callback method
		:rtype: CenterMassVisDrawUserData
		"""
		mfn_dep_node = om.MFnDependencyNode(obj_path.node())
		show_mass = mfn_dep_node.findPlug(CenterMassVis.show_mass_attr, False).asBool()
		show_calc = mfn_dep_node.findPlug(CenterMassVis.show_calc_attr, False).asBool()
		mass_points_plug = mfn_dep_node.findPlug(CenterMassVis.mass_points_attr, False)
		mesh_array_plug = mfn_dep_node.findPlug(CenterMassVis.mesh_attr, False)
		surface_array_plug = mfn_dep_node.findPlug(CenterMassVis.surfaces_attr, False)

		user_data = CenterMassVisDrawUserData()
		user_data.show_mass = show_mass

		for point_index in range(mass_points_plug.numElements()):
			mass_point_plug = mass_points_plug.elementByLogicalIndex(point_index)
			point_plug = mass_point_plug.child(0)
			point = om.MPoint(
				point_plug.child(0).asFloat(),
				point_plug.child(1).asFloat(),
				point_plug.child(2).asFloat(),
				mass_point_plug.child(1).asDouble()
			)
			user_data.mass_points.append(point)

		for mesh_index in range(mesh_array_plug.numElements()):
			mesh_plug = mesh_array_plug.elementByLogicalIndex(mesh_index)
			user_data.mesh_list.append(mesh_plug.asMObject())

		for surface_index in range(surface_array_plug.numElements()):
			surface_plug = surface_array_plug.elementByLogicalIndex(surface_index)
			user_data.surfaces_list.append(surface_plug.asMObject())

		return user_data

	def addUIDrawables(self, obj_path, draw_manager, frame_context, data):
		"""
		Provides access to the MUIDrawManager, which can be used to queue up operations to draw simple UI shapes
		like lines, circles, text, etc.

		This method will only be called when hasUIDrawables() is overridden to return True. It is called after
		prepareForDraw() and carries the same restrictions on the sorts of operations it can perform.

		:param OpenMaya.MDagPath obj_path:
		:param OpenMayaRender.MUIDrawManager draw_manager:
		:param OpenMayaRender.MFrameContext frame_context:
		:param CenterMassVisDrawUserData data:
		"""

		if not data.show_mass:
			return self

		draw_manager.beginDrawable()

		# Calculate the points' center of mass
		points_com = None
		for point in data.mass_points:
			# Draw the point's mass
			draw_manager.text(point, "{}".format(point.w), dynamic=False)

			if points_com is not None:
				points_com = self.calc_center_mass([points_com, point])
			else:
				points_com = point

		# Calculate the center of mass of each connected mesh as well as the collective center
		meshes_com = None
		for mesh_data in data.mesh_list:
			mesh_com = None
			mesh_it = om.MItMeshVertex(mesh_data)
			while not mesh_it.isDone():
				vtx_point = mesh_it.position(DEFAULT_SPACE)
				vtx_point.w = DEFAULT_MASS

				# Draw the vertex' mass
				draw_manager.text(vtx_point, "{}".format(vtx_point.w), dynamic=False)

				# Update the mesh's center of mass
				if mesh_com is not None:
					mesh_com = self.calc_center_mass([mesh_com, vtx_point])
				else:
					mesh_com = vtx_point

				mesh_it.next()

			# Draw the mesh's center of mass
			if mesh_com is not None:
				draw_manager.text(mesh_com, "{}".format(mesh_com.w), dynamic=False)

			# Update the meshes' collective center of mass
			if meshes_com is not None:
				meshes_com = self.calc_center_mass([meshes_com, mesh_com])
			else:
				meshes_com = mesh_com

		# Calculate the center of mass of each connected surface as well as the collective center
		surfaces_com = None
		for surface_data in data.surfaces_list:
			surface_com = None
			surface_cv_it = om.MItSurfaceCV(surface_data)
			while not surface_cv_it.isDone():
				cv_point = surface_cv_it.position(DEFAULT_SPACE)
				cv_point.w = DEFAULT_MASS

				# Draw the control vertex' mass
				draw_manager.text(cv_point, "{}".format(cv_point.w), dynamic=False)

				# Update the surface's center of mass
				if surface_com is not None:
					surface_com = self.calc_center_mass([surface_com, cv_point])
				else:
					surface_com = cv_point

				surface_cv_it.next()

			# Draw the surface's center of mass
			if surface_com is not None:
				draw_manager.text(surface_com, "{}".format(surface_com.w), dynamic=False)

			# Update the surfaces' collective center of mass
			if surfaces_com is not None:
				surfaces_com = self.calc_center_mass([surfaces_com, surface_com])
			else:
				surfaces_com = surface_com

		# Find the center of mass between those of the points', meshes' and surfaces'
		center_of_masses = []
		if points_com is not None and points_com.w > 0.0:
			center_of_masses.append(points_com)

		if meshes_com is not None and meshes_com.w > 0.0:
			center_of_masses.append(meshes_com)

		if surfaces_com is not None and surfaces_com.w > 0.0:
			center_of_masses.append(surfaces_com)

		# Draw the collective center of mass: points, meshes and surfaces
		center_mass_point = self.calc_center_mass(center_of_masses)
		draw_manager.text(center_mass_point, "{}".format(center_mass_point.w))

		draw_manager.endDrawable()
		return self


def initializePlugin(obj):
	plugin = om.MFnPlugin(obj, "Rafael Valenzuela Ochoa", "1.0", "")

	try:
		plugin.registerNode(
			"centerOfMass",
			CenterMassVis.typeId,
			CenterMassVis.creator,
			CenterMassVis.initialize,
			om.MPxNode.kLocatorNode,
			CenterMassVis.drawDBClassification
		)
	except RuntimeError as re:
		sys.stderr.write("Failed to register node CenterMassVis.")
		raise re

	# Register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.registerDrawOverrideCreator(
			CenterMassVis.drawDBClassification,
			CenterMassVis.drawRegistrantId,
			CenterMassVisDrawOverride.creator
		)
	except:
		sys.stderr.write("Failed to register override for node CenterMassVis")
		raise

	try:
		om.MSelectionMask.registerSelectionType("centerOfMassSelection")
		mel.eval("selectType -byName \"centerOfMassSelection\" 1")
	except:
		sys.stderr.write("Failed to register selection mask\n")
		raise


def uninitializePlugin(obj):
	plugin = om.MFnPlugin(obj)
	try:
		plugin.deregisterNode(CenterMassVis.typeId)
	except RuntimeError as re:
		sys.stderr.write("Failed to de-register node CenterMassVis")
		pass

	# De-register Viewport 2.0 implementation
	try:
		omr.MDrawRegistry.deregisterDrawOverrideCreator(
			CenterMassVis.drawDBClassification,
			CenterMassVis.drawRegistrantId
		)
	except:
		sys.stderr.write("Failed to de-register override for node CenterMassVis")
		pass

	try:
		om.MSelectionMask.deregisterSelectionType("centerOfMassSelection")
	except:
		sys.stderr.write("Failed to de-register selection mask\n")
		pass
