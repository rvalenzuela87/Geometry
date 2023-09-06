from decimal import Decimal
import math
from Geometry import Matrix
reload(Matrix)

default_tolerance = 0.0001


def is_matrix_addition_defined(matrix_a, matrix_b):
	return matrix_a.rows == matrix_b.rows and matrix_a.cols == matrix_b.cols


def is_matrix_prod_defined(matrix_a, matrix_b):
	return matrix_a.cols == matrix_b.rows


def is_identity_row(row, tolerance=default_tolerance):
	accum = 0.0

	for e in row:
		accum += e

	return round(Decimal(str(accum)), int(math.log(1.0/tolerance, 10))) == 1.0


def is_zero_row(row, tolerance=default_tolerance):
	accum = 0.0

	for e in row:
		accum += e

	return round(Decimal(str(accum)), int(math.log(1.0/tolerance, 10))) == 0.0


def row_equivalence(matrix_a, matrix_b, tolerance=default_tolerance):
	"""

		:param matrix_a: Matrix instance
		:param matrix_b: Matrix instance

		:return: Boolean
	"""

	'''
		One form of finding out if 2 matrices are row-equivalent, is if the second one can be obtained from a
		series of elementary-row-operations on the first one. For now, we can check if the first one\'s 
		row-reduced-echelon form is equal to the second one
	'''

	matrix_a_rref = row_reduced_echelon(matrix_a, tolerance=tolerance)

	try:
		assert matrix_equality(matrix_a_rref, matrix_b, tolerance=tolerance)
	except(AssertionError, Exception):
		return False
	else:
		return True


def col_equivalence(matrix_a, matrix_b, tolerance=default_tolerance):
	"""

		:param matrix_a: Matrix instance
		:param matrix_b: Matrix instance

		:return: Boolean
	"""

	'''
		One form of finding out if 2 matrices are column-equivalent, is if the second one can be obtained from a
		series of elementary-column-operations on the first one. For now, we can check if the first one\'s 
		column-reduced-echelon form is equal to the second one
	'''

	matrix_a_cref = column_reduced_echelon(matrix_a)

	try:
		assert matrix_equality(matrix_a_cref, matrix_b, tolerance=tolerance)
	except(AssertionError, Exception):
		return False
	else:
		return True


def null_space(matrix):
	"""
	Finds the solution space (null space) = { X(n x 1) | matrix * X = 0 } of the matrix received as argument
		:param matrix: Matrix instance
		:return: n x 1 Matrix instance, where n = # of columns of the matrix received as argument.
	"""

	aug_matrix = matrix_augment(matrix, Matrix.Matrix(matrix.rows, 1, [0.0 for __ in range(matrix.rows)]))
	matrix_rref = row_reduced_echelon(aug_matrix)

	pass


def row_space(matrix, y=None):
	"""
	Returns the row space = { y * matrix | y(1 x m) } of the matrix received as argument.

		:param matrix: Matrix instance
		:param y: Matrix instance with dimension 1 x m,  where m = # number of rows of matrix. If one is not provided,
				then a 1 x m matrix with 1's as elements will be used

		:return: 1 x n Matrix instance, where n = # of columns of the matrix received as argument
	"""

	if y is None:
		y = Matrix.Matrix(1, matrix.rows, [1.0 for __ in range( matrix.rows )])
	else:
		try:
			assert y.rows == 1
		except AssertionError:
			raise ValueError("Argument for parameter y is expected to be a matrix with dimension 1 x m, where m = matrix\' rows. Exiting... ")
		except AttributeError:
			raise ValueError("Argument for parameter y is expected to be of type Matrix. Exiting...")

		return matrix_prod(y, matrix)


def in_row_space(k, matrix):
	"""
	Finds weather matrix k is in the row space = { k(1 x n} | y * matrix = k } of the matrix passed as the second argument.
		:param k: Matrix instance with dimension 1 x m, where m = matrix\'s # of rows
		:param matrix: Matrix instance

		:return: Boolean
	"""

	matrix_t = matrix_transpose(matrix)
	k_t = matrix_transpose(k)

	try:
		__, solution_matrix = in_column_space(k_t, matrix_t)

		return True, matrix_transpose(solution_matrix)
	except Exception:
		return False


def column_space(matrix, x=None):
	"""
	Returns the column space = { K(m x 1) | matrix * x = K } of the matrix received as argument.

		:param matrix: Matrix instance
		:param x: Matrix instance with dimension 1 x m,  where m = # number of rows of matrix. If one is not provided,
				then a 1 x m matrix with 1's as elements will be used

		:return: m x 1 Matrix instance, where m = # of rows of the matrix received as argument
	"""

	if x is None:
		x = Matrix.Matrix(matrix.cols, 1, [1.0 for __ in range( matrix.cols )])
	else:
		try:
			assert x.cols == 1
		except AssertionError:
			raise ValueError("Argument for parameter x is expected to be a matrix with dimension n x 1, where n = matrix\' columns. Exiting... ")
		except AttributeError:
			raise ValueError("Argument for parameter x is expected to be of type Matrix. Exiting...")

	return matrix_prod( matrix, x )


def in_column_space(k, matrix, tolerance=default_tolerance):
	"""
	Finds weather matrix k is in the column space = { k(m x 1} | matrix * x = k } of the matrix passed as the second argument.
		:param k: Matrix instance with dimension m x 1, where m = matrix\'s # of rows
		:param matrix: Matrix instance

		:return: Boolean
	"""

	matrix_augm_rref = row_reduced_echelon(matrix_augment(matrix, k), tolerance=tolerance)
	x_elements = []

	for ri in range(matrix_augm_rref.rows):
		matrix_augm_rref_row = [matrix_augm_rref.get(ri, ci) for ci in range(matrix_augm_rref.cols)]

		if is_identity_row(matrix_augm_rref_row[0:-1]) is True:
			x_elements.append(matrix_augm_rref_row[-1])
		else:
			if is_zero_row(matrix_augm_rref_row[0:-1]) is True:
				result = matrix_augm_rref_row[-1]

				if not round(Decimal(str(result)), int(math.log(1.0/tolerance, 10))) == 0.0:
					''' A zero-row cannot have non-zero element in the k-augmented-part '''
					return False
				else:
					continue
			else:
				continue

	matrix_x = Matrix.Matrix(matrix.cols, 1, x_elements)

	return True, matrix_x
	try:
		matrix_times_x = matrix_prod(matrix, matrix_x)
	except Exception:
		''' matrix * matrix_x is not defined... '''
		return False

	try:
		assert matrix_equality(matrix_times_x, k, 0.0001)
	except(AssertionError, Exception) as exc:
		print("Matrix solution is incorrect: %s" % exc.message)
		print("-- {}".format(matrix_times_x))
		print("-- {}".format(k))
		return False
	else:
		return True, matrix_x


def elementary_row_operation_1(matrix, row_i_index, row_j_index):
	"""
	Performs an elementary row operation (ERO) of type I: Row i and row j are interchanged

		:param matrix: Matrix instance
		:param row_i_index: Integer
		:param row_j_index: Integer

		:return: Matrix instance

		:raise: IndexError
	"""

	matrix_cp = Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements())
	matrix_cp.set_row(row_i_index, [e for e in matrix.row(row_j_index)])
	matrix_cp.set_row(row_j_index, [e for e in matrix.row(row_i_index)])

	return matrix_cp


def elementary_row_operation_2(matrix, row_index, scalar):
	"""
	Performs an elementary row operation (ERO) of type II: Row i is multiplied by scalar (scalar != 0).

		:param matrix: Matrix instance
		:param row_index: Integer
		:param scalar: Integer or Float

		:return: Matrix instance

		:raise: ValueError
	"""

	scalar = float(scalar)
	'''try:
		assert not scalar == 0.0
	except AssertionError:
		raise ValueError("Scalar must be greater or less but not equal to 0. Exiting...")'''

	elements = [re * scalar for re in matrix.row(row_index)]

	return Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements()).set_row(row_index, elements)


def elementary_row_operation_3(matrix, row_i_index, row_j_index, scalar_k ):
	"""
	Performs an elementary row operation (ERO) of type III: Row j is replaced by itself plus k times Row i

		:param matrix: Matrix instance
		:param row_i_index: Integer
		:param row_j_index: Integer
		:param scalar_k: Float

		:return: Matrix instance

		:raise: ValueError
	"""

	matrix_cp = Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements())

	row_i = elementary_row_operation_2(matrix_cp, row_i_index, scalar_k ).row( row_i_index)
	row_j = matrix_cp.row(row_j_index)

	matrix_cp.set_row(row_j_index, [row_i[ci] + row_j[ci] for ci in range( matrix_cp.cols)])

	return matrix_cp


def row_reduced_echelon(matrix, tolerance=default_tolerance):
	"""
	Finds the row-reduced-echelon form for the matrix received as argument.

		:param matrix: Matrix instance
		:return: Matrix instance
	"""
	matrix_cp = Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements())

	for ri in range(matrix_cp.rows):
		''' Row pivot '''
		ci = ri
		# print("**** Start Row %i *****" % ri)
		try:
			elements = matrix_cp.elements()
			ri_acum = ri
			row_col_value = matrix_cp.get(ri, ci)
			# print("---- Row-column value: {} | Rounded: {}".format(row_col_value, round(Decimal(str(row_col_value)), int(math.log(1.0/tolerance, 10)))))

			while round(Decimal(str(row_col_value)), int(math.log(1.0/tolerance, 10))) == 0.0:
				ri_acum += 1

				try:
					matrix_cp = elementary_row_operation_1(matrix_cp, ri, ri_acum)
				except IndexError:
					''' Reset matrix before row operations '''
					matrix_cp.set_elements(elements)
					ri_acum = ri
					ci += 1

				row_col_value = matrix_cp.get(ri, ci)

		except IndexError as exc:
			''' Row at ri is a zero row '''
			break

		# print("---- Prev: {}".format(matrix_cp))
		# matrix_cp = elementary_row_operation_2(matrix_cp, ri, 1.0/round(Decimal(str(matrix_cp.get(ri, ci))), 4))
		matrix_cp = elementary_row_operation_2(matrix_cp, ri, 1.0/matrix_cp.get(ri, ci))
		# print("-- ERO2: {}".format(matrix_cp))
		''' Zero pivot column '''
		rows = [i for i in range(ri)]

		for i in range(ri + 1, matrix_cp.rows):
			rows.append(i)

		for rii in rows:
			matrix_cp = elementary_row_operation_3(matrix_cp, ri, rii, 0.0 - matrix_cp.get(rii, ci))
			# print("-- ERO 3: {}".format(matrix_cp))
		# print("**** End Row %i *****" % ri)
		# print("**********************")
	return matrix_cp


def elementary_column_operation_1(matrix, col_i_index, col_j_index):
	"""
	Performs an elementary row operation (ERO) of type I: Column i and column j are interchanged

		:param matrix: Matrix instance
		:param col_i_index: Integer
		:param col_j_index: Integer

		:return: Matrix instance

		:raise: IndexError
	"""

	matrix_cp = Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements())
	matrix_cp.set_col(col_i_index, [ e for e in matrix.col( col_j_index)])
	matrix_cp.set_col(col_j_index, [ e for e in matrix.col( col_i_index)])

	return matrix_cp


def elementary_column_operation_2(matrix, col_index, scalar):
	"""
	Performs an elementary column operation (ECO) of type II: Column i is multiplied by scalar (scalar != 0 ).

		:param matrix: Matrix instance
		:param col_index: Integer
		:param scalar: Float

		:return: Matrix instance

		:raise: ValueError
	"""

	scalar = float(scalar)

	'''try:
		assert not scalar == 0.0
	except AssertionError:
		raise ValueError("Scalar must be greater or less but not equal to 0. Exiting...")'''

	elements = [ ce * scalar for ce in matrix.col( col_index ) ]

	return Matrix.Matrix( matrix.rows, matrix.cols, matrix.elements() ).set_col( col_index, elements )


def elementary_column_operation_3(matrix, col_i_index, col_j_index, scalar_k):
	"""
	Performs an elementary column operation (ECO) of type III: Column j is replaced by itself plus k times Column i

		:param matrix: Matrix instance
		:param col_i_index: Integer
		:param col_j_index: Integer
		:param scalar_k: Float

		:return: Matrix instance

		:raise: ValueError
	"""

	matrix_cp = Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements())

	col_i = elementary_column_operation_2(matrix_cp, col_i_index, scalar_k ).col(col_i_index)
	col_j = matrix_cp.col(col_j_index)

	matrix_cp.set_col(col_j_index, [col_i[ri] + col_j[ri] for ri in range( matrix_cp.rows)])

	return matrix_cp


def column_reduced_echelon(matrix, tolerance=default_tolerance):
	"""
	Finds the column-reduced-echelon form for the matrix received as argument.

		:param matrix: Matrix instance
		:return: Matrix instance
	"""
	matrix_cp = Matrix.Matrix(matrix.rows, matrix.cols, matrix.elements())

	for ci in range(matrix_cp.cols):
		''' Column pivot '''
		ri = ci

		try:
			elements = matrix_cp.elements()
			ci_acum = ci
			row_col_value = matrix_cp.get(ri, ci)

			while round(Decimal(str(row_col_value)), int(math.log(1.0/tolerance, 10))) == 0.0:
				ci_acum += 1

				try:
					matrix_cp = elementary_column_operation_1(matrix_cp, ci, ci_acum)
				except IndexError:
					''' Reset matrix before column operations '''
					matrix_cp.set_elements(elements)
					ci_acum = ci
					ri += 1

				row_col_value = matrix_cp.get(ri, ci)

		except IndexError:
			''' Row at ri is a zero row '''
			break

		matrix_cp = elementary_column_operation_2(matrix_cp, ci, 1.0/float(matrix_cp.get(ri, ci)))

		''' Zero pivot column '''
		cols = [i for i in range( ci )]
		cols.extend([j for j in range(ci + 1, matrix_cp.cols)])

		for cii in cols:
			matrix_cp = elementary_column_operation_3( matrix_cp, ci, cii, 0.0 - float(matrix_cp.get( ri, cii )) )

	return matrix_cp


def has_inverse(matrix):
	"""
	Only square matrices can have an inverse but not all square matrices have an inverse

		:param matrix: Matrix instance

		:return: Boolean
	"""

	try:
		''' Matrix has to be square to proceed...'''
		assert matrix.rows == matrix.cols

		''' Matrix has to be row equivalent to the identity '''
		assert row_equivalence( matrix, matrix_identity( matrix.rows ) )
	except AssertionError:
		return False
	else:
		return True


def matrix_equality(matrix_a, matrix_b, tolerance=None):
	"""
	Compares both matrices and weighs weather they are equal.

		:param matrix_a: Matrix instance
		:param matrix_b: Matrix instance

		:return: Boolean

		:raise: Exception
	"""

	matrix_a_elements = matrix_a.elements()
	matrix_b_elements = matrix_b.elements()

	try:
		assert matrix_a.rows == matrix_b.rows and matrix_a.cols == matrix_b.cols and len(matrix_a_elements) == len(matrix_b_elements)
	except AssertionError:
		if not matrix_a.rows == matrix_b.rows:
			raise Exception("The number of rows on both matrices are not equal")
		elif not matrix_a.cols == matrix_b.cols:
			raise Exception("The number of columns on both matrices are not equal")
		else:
			raise Exception("The number of elements on both matrices are not equal")
	else:
		if tolerance is not None:
			try:
				for i in range(len(matrix_a_elements)):
					assert abs(matrix_a_elements[i] - matrix_b_elements[i]) <= tolerance
			except AssertionError:
				raise Exception("Values differ between matrices")
			else:
				return True
		else:
			return matrix_a_elements == matrix_b_elements

def matrix_scalar_prod( matrix, scalar ):
	return Matrix.Matrix( matrix.rows, matrix.cols, [ e * scalar for e in matrix.elements() ] )


def matrix_add( matrix_a, matrix_b ):
	try:
		assert is_matrix_addition_defined( matrix_a, matrix_b )
	except AssertionError:
		raise Exception("Matrix addition is not defined for matrices A(%ix%i) and B(%ix%i)" % (matrix_a.rows, matrix_a.cols, matrix_b.rows, matrix_b.cols) )

	elements = []
	rows = matrix_a.rows
	cols = matrix_a.cols

	[ [ elements.append( matrix_a.get(ri, ci) + matrix_b.get( ri, ci ) ) for ri in range( matrix_a.rows ) ] for ci in range( matrix_a.cols ) ]

	return Matrix.Matrix( rows, cols, elements )


def matrix_prod( matrix_a, matrix_b ):
	try:
		assert is_matrix_prod_defined( matrix_a, matrix_b )
	except AssertionError:
		raise Exception( "Matrix product for matrices A(%ix%i) and B(%ix%i) is not defined" )

	elements = []

	for a_ri in range( matrix_a.rows ):
		for b_ci in range( matrix_b.cols ):
			t = 0.0

			for a_ci in range( matrix_a.cols ):
				t += matrix_a.get( a_ri, a_ci ) * matrix_b.get( a_ci, b_ci )

			elements.append( t )

	return Matrix.Matrix( matrix_a.rows, matrix_b.cols, elements )


def matrix_transpose( matrix ):
	elements = []

	[ [ elements.append( matrix.get( ri, ci ) ) for ri in range( matrix.rows ) ] for ci in range( matrix.cols ) ]

	return Matrix.Matrix( matrix.cols, matrix.rows, elements )


def matrix_augment( matrix_a, matrix_b ):
	try:
		assert matrix_a.rows == matrix_b.rows
	except AssertionError:
		raise Exception( "The number of rows of both matrices are not equal: A(%ix%i) B(%ix%i)" % ( matrix_a.rows, matrix_a.cols, matrix_b.rows, matrix_b.cols ) )

	elements = []

	for ri in range( matrix_a.rows ):
		[ elements.append(e) for e in matrix_a.row(ri) ]
		[ elements.append(e) for e in matrix_b.row(ri) ]

	return Matrix.Matrix( matrix_a.rows, matrix_a.cols + matrix_b.cols, elements )


def matrix_identity( order ):
	identity = Matrix.Matrix( order, order, [0.0 for i in range( order * order )] )

	for ri in range( identity.rows ):
		identity.set( ri, ri, 1.0)

	return identity


def matrix_inverse( matrix ):
	try:
		assert has_inverse( matrix )
	except AssertionError:
		raise Exception( "The %ix%i matrix received does\'nt have an inverse. Exiting..." % ( matrix.rows, matrix.cols ) )

	rref_matrix 	= row_reduced_echelon( matrix_augment( matrix, matrix_identity( matrix.rows ) ) )
	inv_matrix 		= Matrix.Matrix( matrix.rows, matrix.cols )

	[ [ inv_matrix.set( ri - matrix.rows, ci - matrix.cols, rref_matrix.get(ri, ci) ) for ci in range( matrix.cols, rref_matrix.cols ) ] for ri in range( rref_matrix.rows ) ]

	return inv_matrix
