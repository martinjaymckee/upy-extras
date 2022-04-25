
class Vector:
    def __init__(self, data=None):
        self.__data = data
        
    def __len__(self):
        return len(self.__data)
        
    def __str__(self):
        return '{}'.format(self.__data)

    def append(self, value):
        return self.__data.append(value)
       
    @micropython.native        
    def __getitem__(self, idx):
        len_self = len(self)
        if (idx < 0) or (idx > (len_self - 1)):
            raise Exception('Invalid get index ({}) in vector of length {}'.format(idx, len_self))
        return self.__data[idx]

    @micropython.native        
    def __setitem__(self, idx, val):
        len_self = len(self)
        if (idx < 0) or (idx > (len_self - 1)):
            raise Exception('Invalid set index ({}) in vector of length {}'.format(idx, len_self))
        self.__data[idx] = val
        return val

    @micropython.native        
    def __neg__(self):
        v = self.__class__([-d for d in self.__data])
        return v

    @micropython.native
    def __add__(self, other):
        if isinstance(other, Vector):
            len_self, len_other = len(self), len(other)
            if not (len_self == len_other):
                raise Exception('Invalid vector sizes for addition {} and {}'.format(len_self, len_other))                
            v = self.__class__([(s+o) for s, o in zip(self.__data, other.__data)])
            return v
    
    @micropython.native
    def __mul__(self, other):
        v = None
        if isinstance(other, Vector):
            v = Matrix()
            for scalar in self.__data:
                row_data = [(scalar * d) for d in other.__data]
                v.append_row(*row_data)
        else:
            v = self.__class__(data=[other*d for d in self.__data])
        return v

    @micropython.native
    def dot(self, other):
        if isinstance(other, Vector):
            len_self, len_other = len(self), len(other)
            if not (len_self == len_other):
                raise Exception('Invalid vector sizes for addition {} and {}'.format(len_self, len_other))                
            return sum([(s*o) for s, o in zip(self.__data, other.__data)])
    
    
class Matrix:
    class RowIterator:
        def __init__(self, obj):           
            self.__obj = obj
            self.__row = 0
            
        def __next__(self):
            row = self.__row
            if row < self.__obj.__shape[0]:
                self.__row += 1
                return self.__obj[row]
            raise StopIteration

    class AccessProxy:
        def __init__(self, obj, row):
            self.__obj = obj
            self.__row = row
        
        @property
        def dims(self):
            return self.__obj.__dims
        
        @property
        def shape(self):
            return self.__obj.__shape
        
        def __str__(self):
            row = self.__row
            rows, columns = self.__obj.__shape
            values = ['{}'.format(v) for v in self.__obj.__data[row*columns:(row+1)*columns]]
            return '[{}]\n'.format(',\t'.join(values))
        
        @micropython.native
        def __iter__(self):
            return Matrix.ColumnIterator(self.__obj, self.__row)
    
        @micropython.native        
        def __getitem__(self, column):
            rows, columns = self.__obj.shape
            idx = self.__row * columns + column    
            return self.__obj.__data[idx]
        
        @micropython.native        
        def __setitem__(self, column, value):
            rows, columns = self.__obj.shape
            idx = self.__row * columns + column    
            self.__obj.__data[idx] = value      

    class ColumnIterator:
        def __init__(self, obj, row):
            self.__obj = obj
            self.__column = 0
            columns = self.__obj.__shape[1]
            self.__columns = columns
            self.__base = row * columns
            self.__data = self.__obj.__data

        @micropython.native
        def __next__(self):
            column = self.__column
            rows, columns = self.__obj.__shape
            if column < columns:
                self.__column += 1
                idx = self.__base + column
                return self.__data[idx] #Matrix.ValueDescriptor(self.__data, idx)
            raise StopIteration
        
    def __init__(self, data=None, dims=2):
        self.__dims = dims
        self.__shape = None
        self.__data = []
        if data is not None:
            self.__from_data(data)
            
    @property
    def dims(self):
        return self.__dims
    
    @property
    def shape(self):
        return self.__shape
    
    @property
    def data(self):
        return self.__data
    
    @micropython.native
    def __str__(self):
        text = ''
        rows, columns = self.shape
        for row in range(rows):
            values = ['{}'.format(v) for v in self.__data[row*columns:(row+1)*columns]]
            text += '[{}]\n'.format(',\t'.join(values))
        return text

    @micropython.native
    def __iter__(self):
        return Matrix.RowIterator(self)

    @micropython.native        
    def __getitem__(self, row):
        return Matrix.AccessProxy(self, row)

    @micropython.native        
    def append_row(self, *row_data):
        shape = self.__shape
        if shape is None:
            shape = (1, len(row_data))
        else:
            rows, columns = shape
            if not columns == len(row_data):
                raise Exception # TODO: THIS SHOULD BE A MORE SPECIALIZED EXCEPTION                
            shape = (rows + 1, columns)
        self.__data.extend(row_data)            
        self.__shape = shape

    @micropython.native
    def transpose(self):
        m = self.__class__()
        rows, columns = self.__shape
        for row in range(columns):
            row_data = [self.__data[(c*columns) + row] for c in range(rows)]
            m.append_row(*row_data)
        return m

    @micropython.native
    def __neg__(self):
        m = self.__class__()
        m.__data = [-d for d in self.__data]
        m.__shape = self.__shape
        m.__dims = self.__dims
        return m

    @micropython.native
    def __neg__(self):
        m = self.__class__()
        m.__data = [-d for d in self.__data]
        m.__shape = self.__shape
        m.__dims = self.__dims
        return m

    @micropython.native
    def __add__(self, other):
        if isinstance(other, Matrix):
            if not (self.__shape == other.__shape):
                raise Exception('Invalid matrix sizes for addition {} and {}'.format(self.__shape, other.__shape))

            m = self.__class__()
            m.__data = [(s+o) for s, o in zip(self.__data, other.__data)]
            m.__shape = self.__shape
            m.__dims = self.__dims
            return m

    @micropython.native
    def __sub__(self, other):
        if isinstance(other, Matrix):
            if not (self.__shape == other.__shape):
                raise Exception('Invalid matrix sizes for other {} and {}'.format(self.__shape, other.__shape))

            return self.__add__(-other)

    @micropython.native
    def __mul__(self, other):
        if isinstance(other, Matrix):
            if not (self.__shape[1] == other.__shape[0]):
                raise Exception('Invalid matrix sizes for multiplication {} and {}'.format(self.__shape, other.__shape))
            m = self.__class__()
            (rows, src_columns), columns = self.__shape, other.__shape[1]
            for row in range(rows):
                row_data = []
                for column in range(columns):
                    dot = 0
                    for src_column in range(src_columns):
                        dot += (self[row][src_column] * other[src_column][column])
                    row_data.append(dot)
                m.append_row(*row_data)
            return m
        return None
    
    @micropython.native
    def __from_data(self, data):
        shape = []
        shape_initialized = False
        for d in data: # TODO: THIS ASSUMES A 2D MATRIX
            if not shape_initialized:
                shape.append(1)
                shape.append(len(d))
                shape_initialized = True
            else:
                if not len(d) == shape[1]:
                    raise Exception # TODO: THIS SHOULD BE A MORE SPECIALIZED EXCEPTION
                shape[0] += 1
            self.__data.extend(d)
        self.__shape = tuple(shape)
        
       
if __name__ == '__main__':
    test_data = [ [1, 2, 3], [4, 5, 6], [7, 8, 9]]
    print(test_data)
    m = Matrix(data=test_data)
    print(m.data)
    print(m.shape)
    print()
    print(m)
    
    print(m[0][1])
    
    m2 = Matrix()
    m2.append_row(0, 2, 4)
    print(m2.shape)
    print(m2)
    m2.append_row(1, 3, 5)
    m2.append_row(2, 4, 6)
    print(m2.shape)
    print(m2)
 
    try:
        m2.append_row(4, 4, 4, 4)
    except:
        print('Attempted to append an invalid row!')
    print(m2.shape)
    print(m)
    print(m2)
    print(m*m2)
    print(m-m2)
    
#     for row, proxy in enumerate(m):
#         for column, v in enumerate(proxy):
#             print('{} '.format(v), end='')
#     print('\n\n')
# 
#     for row in range(3):
#         for column in range(3):
#             m2[row][column] += 1
#     print(m2.shape)
#     print(m2)
    
#     print()
#     print(m2.transpose())
#     
#     print(m2 * m)
    
    c = Matrix()
    c.append_row(1, 2, 3)
    c.append_row(4, 5, 6)
    
    d = c.transpose()
    
    print(c)
    print(d)
    print(c*d)
    
    A = Vector([1, 2, 3])
    B = Vector([4, 5, 6])
    print(A)
    print(B)
    print(A*B)
    
    