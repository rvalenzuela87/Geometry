from decimal import Decimal


class Matrix(object):
	rows = 0
	cols = 0
	decimals = 6

	__elements = []

	def __str__(self):
		return "{}".format(self.__elements)

	def __init__(self, rows, columns, elements=None):
		super(Matrix, self).__init__()

		self.rows = rows
		self.cols = columns

		elements = elements if elements else []
		if len(elements) > 0:
			self.set_elements([e for e in elements])

		else:
			self.__elements = [0.0 for __ in range(rows * columns)]

	def get(self, row, col):
		try:
			return self.__elements[(row * self.cols) + col]
		except IndexError:
			if row >= self.rows:
				raise IndexError(
					"Received a row index greater than the rows contained (indices are zero-based): %i > %i" % (
					row, self.rows - 1))
			elif col >= self.cols:
				raise IndexError(
					"Received a column index greater than the columns contained (indices are zero-based): %i > %i" % (
					col, self.cols - 1))
			else:
				raise IndexError("No element at row %i and col %i" % (row, col))

	def row(self, index):
		return [self.get(index, ci) for ci in range(self.cols)]

	def col(self, index):
		return [self.get(ri, index) for ri in range(self.rows)]

	def elements(self):
		return self.__elements

	def set_elements(self, elements):
		try:
			assert len(elements) == self.rows * self.cols

			self.__elements = [round(Decimal(str(e)), Matrix.decimals) for e in elements]
		# self.__elements = [round(float(int(e * 10000000))/10000000.0, 7) for e in elements]
		except AssertionError:
			raise Exception("Not enough elements received")

		return self

	def set(self, row, col, value):
		try:
			self.__elements[(row * self.cols) + col] = round(Decimal(str(value)), Matrix.decimals)
		# self.__elements[(row * self.cols) + col] = round(float(int(value * 10000000))/10000000.0, 7)
		except IndexError:
			if row >= self.rows:
				raise IndexError(
					"Received a row index greater than rows contained (indices are zero-based): %i > %i" % (
					row, self.rows))
			elif col >= self.cols:
				raise IndexError(
					"Received a column index greater than the columns contained (indices are zero-based): %i > %i" % (
					col, self.cols))
			else:
				raise IndexError("No element at row %i and col %i" % (row, col))

		return self

	def set_row(self, index, elements):
		try:
			for ci in range(self.cols):
				self.set(index, ci, elements[ci])
		except IndexError as ie:
			if len(elements) < self.cols - 1:
				raise IndexError(
					"The total elements received is not equal to the total columns on the matrix. Exiting...")
			else:
				raise ie

		return self

	def set_col(self, index, elements):
		try:
			for ri in range(self.rows):
				self.set(ri, index, elements[ri])
		except IndexError as ie:
			if len(elements) < self.rows - 1:
				raise Exception("The total elements received is not equal to the total rows on the matrix. Exiting...")
			else:
				raise ie

		return self
