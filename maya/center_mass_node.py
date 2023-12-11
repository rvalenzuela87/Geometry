import sys
import math
from collections import namedtuple
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr

maya_useNewAPI = True
DEFAULT_MASS = 1.0


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
	mass_attr = None
	center_mass_attr = None
	mass_sum_attr = None

	def __init_(self):
		super(CenterMassVis, self).__init__()

	@staticmethod
	def initialize():
		mfn_num_attr = om.MFnNumericAttribute()
		mfn_comp_attr = om.MFnCompoundAttribute()
		mfn_enum_attr = om.MFnEnumAttribute()

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

		CenterMassVis.center_mass_attr = mfn_num_attr.createPoint("centerOfMass", "centerOfMass")
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = (0.0, 0.0, 0.0)

		CenterMassVis.mass_sum_attr = mfn_num_attr.create("massSum", "massSum", om.MFnNumericData.kDouble)
		mfn_num_attr.writable = False
		mfn_num_attr.storable = False
		mfn_num_attr.keyable = False
		mfn_num_attr.default = 0.0

		CenterMassVis.addAttribute(CenterMassVis.show_mass_attr)
		CenterMassVis.addAttribute(CenterMassVis.show_calc_attr)
		CenterMassVis.addAttribute(CenterMassVis.mass_points_attr)
		CenterMassVis.addAttribute(CenterMassVis.center_mass_attr)
		CenterMassVis.addAttribute(CenterMassVis.mass_sum_attr)

		CenterMassVis.attributeAffects(CenterMassVis.point_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.mass_attr, CenterMassVis.center_mass_attr)
		CenterMassVis.attributeAffects(CenterMassVis.point_attr, CenterMassVis.mass_sum_attr)
		CenterMassVis.attributeAffects(CenterMassVis.mass_attr, CenterMassVis.mass_sum_attr)

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
		if plug.attribute() not in (self.center_mass_attr, self.mass_sum_attr):
			data_block.setClean(plug)
			return

		mass_points = []
		mass_points_input_array = data_block.inputArrayValue(self.mass_points_attr)
		while not mass_points_input_array.isDone():
			mass_point_data = mass_points_input_array.inputValue()
			mass_points.append(
				om.MPoint(
					*mass_point_data.child(self.point_attr).asDouble3(),
					mass_point_data.child(self.mass_attr).asDouble()
				)
			)
			mass_points_input_array.next()

		center_mass = self.calc_center_mass(mass_points)
		center_mass_data = data_block.outputValue(self.center_mass_attr)
		mass_sum_data = data_block.outputValue(self.mass_sum_attr)

		center_mass_data.set3Float(center_mass.x, center_mass.y, center_mass.z)
		mass_sum_data.setFloat(center_mass.w)

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

		user_data = CenterMassVisDrawUserData()
		user_data.show_mass = show_mass

		for point_index in range(mass_points_plug.numElements()):
			mass_point_plug = mass_points_plug.elementByLogicalIndex(point_index)
			point_plug = mass_point_plug.child(0)
			point = om.MPoint(
				point_plug.child(0).asDouble(),
				point_plug.child(1).asDouble(),
				point_plug.child(2).asDouble(),
				mass_point_plug.child(1).asDouble()
			)
			user_data.mass_points.append(point)

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
		for point in data.mass_points:
			draw_manager.text(point, "{}".format(point.w), dynamic=False)

		center_mass_point = self.calc_center_mass(data.mass_points)
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
