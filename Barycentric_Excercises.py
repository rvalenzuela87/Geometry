import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

maya_useNewAPI = True

import maya.cmds as cmds

import Geometry.Vector_Utils as vu
import Geometry.Barycentric_Utils as bu

def figureInTriangle():
	figureDagPath = om.MGlobal.getActiveSelectionList().getDagPath(0).extendToShape()
	v1 = om.MGlobal.getActiveSelectionList().getDagPath(1)
	v2 = om.MGlobal.getActiveSelectionList().getDagPath(2)
	v3 = om.MGlobal.getActiveSelectionList().getDagPath(3)

	points  = []
	components = om.MObject()
	weights = om.MDoubleArray()

	if figureDagPath.node().apiType() == om.MFn.kNurbsCurve:
		mFnNurbsCurve   = om.MFnNurbsCurve(figureDagPath)
		points          = [ ( p[0], p[1], p[2] ) for p in mFnNurbsCurve.cvPositions() ]
		components      = mFnNurbsCurve.cvs( 0, mFnNurbsCurve.numCVs - 1 )

	elif figureDagPath.node().apiType() == om.MFnNurbsSurface:
		mFnNurbsSurface = om.MFnNurbsSurface( figureDagPath )
		points          = [ ( p[0], p[1], p[2] ) for p in mFnNurbsSurface.cvPositions( om.MSpace.kWorld ) ]

		mSelList = om.MSelectionList()
		mSelList.add( ( figureDagPath, mFnNurbsSurface.cvsInU( 0, mFnNurbsSurface.numCVsInU - 1 ) ) )
		mSelList.add( ( figureDagPath, mFnNurbsSurface.cvsInV( 0, mFnNurbsSurface.numCVsInV - 1 ) ) )

		__, components = mSelList.getComponent(0)
	elif figureDagPath.node().apiType() == om.MFn.kMesh:
		mFnMesh = om.MFnMesh( figureDagPath )
		mItMeshVertex = om.MItMeshVertex( figureDagPath )
		mSelList = om.MSelectionList()

		while not mItMeshVertex.isDone():
			mSelList.add( ( figureDagPath, mItMeshVertex.currentItem() ) )
			mItMeshVertex.next()

		points  = [ ( p[0], p[1], p[2] ) for p in mFnMesh.getPoints( om.MSpace.kWorld ) ]
		__, components = mSelList.getComponent(0)

	else:
		raise Exception( "Figure type not supported. Expected mesh, curve or surface. Exiting..." )

	triangle = [
		om.MFnTransform(v1).translation(om.MSpace.kWorld),
		om.MFnTransform(v2).translation(om.MSpace.kWorld),
		om.MFnTransform(v3).translation(om.MSpace.kWorld)
	]

	[ [ weights.append( bc ) for bc in bu.triangle_barycentric_coord( vu.vector_projection_on_plane( p, triangle[0], triangle[1] )[1], triangle ) ] for p in points ]

	prevSel = cmds.ls(sl=True)
	cmds.select(cl=True)

	clstr = cmds.skinCluster(v1.fullPathName(), figureDagPath.fullPathName()).pop()
	cmds.skinCluster(clstr, e=True, ai=v2.fullPathName(), wt=0.0)
	cmds.skinCluster(clstr, e=True, ai=v3.fullPathName(), wt=0.0)

	mSelList = om.MSelectionList()
	mSelList.add(clstr)

	clstr = mSelList.getDependNode(0)

	mFnSkinCluster = oma.MFnSkinCluster(clstr)
	influences = om.MIntArray()
	[ influences.append(mFnSkinCluster.indexForInfluenceObject(v)) for v in [v1, v2, v3] ]

	mFnSkinCluster.setWeights( figureDagPath, components, influences, weights, False, False )