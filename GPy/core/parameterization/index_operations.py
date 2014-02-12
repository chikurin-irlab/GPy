'''
Created on Oct 2, 2013

@author: maxzwiessele
'''
import numpy
from numpy.lib.function_base import vectorize
from param import Param
from collections import defaultdict

class ParamDict(defaultdict):
    def __init__(self):
        """
        Default will be self._default, if not set otherwise
        """
        defaultdict.__init__(self, self.default_factory)
        
    def __getitem__(self, key):
        try:
            return defaultdict.__getitem__(self, key)
        except KeyError:
            for a in self.iterkeys():
                if numpy.all(a==key) and a._parent_index_==key._parent_index_:
                    return defaultdict.__getitem__(self, a)
            raise        
        
    def __contains__(self, key):
        if defaultdict.__contains__(self, key):
            return True
        for a in self.iterkeys():
            if numpy.all(a==key) and a._parent_index_==key._parent_index_:
                return True
        return False

    def __setitem__(self, key, value):
        if isinstance(key, Param):
            for a in self.iterkeys():
                if numpy.all(a==key) and a._parent_index_==key._parent_index_:
                    return super(ParamDict, self).__setitem__(a, value)
        defaultdict.__setitem__(self, key, value)

class SetDict(ParamDict):
    def default_factory(self):
        return set()

class IntArrayDict(ParamDict):
    def default_factory(self):
        return numpy.int_([])

class ParameterIndexOperations(object):
    '''
    Index operations for storing param index _properties
    This class enables index with slices retrieved from object.__getitem__ calls.
    Adding an index will add the selected indexes by the slice of an indexarray
    indexing a shape shaped array to the flattened index array. Remove will
    remove the selected slice indices from the flattened array.
    You can give an offset to set an offset for the given indices in the
    index array, for multi-param handling.
    '''
    def __init__(self):
        self._properties = IntArrayDict()
        #self._reverse = collections.defaultdict(list)
        
    def __getstate__(self):
        return self._properties#, self._reverse
        
    def __setstate__(self, state):
        self._properties = state[0]
        # self._reverse = state[1]

    def iteritems(self):
        return self._properties.iteritems()
    
    def items(self):
        return self._properties.items()

    def properties(self):
        return self._properties.keys()

    def iterproperties(self):
        return self._properties.iterkeys()
    
    def shift(self, start, size):
        for ind in self.iterindices():
            toshift = ind>=start
            if toshift.size > 0:
                ind[toshift] += size
    
    def clear(self):
        self._properties.clear()
    
    def size(self):
        return reduce(lambda a,b: a+b.size, self.iterindices(), 0)    
    
    def iterindices(self):
        return self._properties.itervalues()
    
    def indices(self):
        return self._properties.values()

    def properties_for(self, index):
        return vectorize(lambda i: [prop for prop in self.iterproperties() if i in self[prop]], otypes=[list])(index)
        
    def add(self, prop, indices):
        try:
            self._properties[prop] = combine_indices(self._properties[prop], indices)
        except KeyError: 
            self._properties[prop] = indices
    
    def remove(self, prop, indices):
        if prop in self._properties:
            diff = remove_indices(self[prop], indices)
            removed = numpy.intersect1d(self[prop], indices, True)
            if not index_empty(diff):
                self._properties[prop] = diff
            else:
                del self._properties[prop]
            return removed.astype(int)
        return numpy.array([]).astype(int)
    
    def __getitem__(self, prop):
        return self._properties[prop]
    
    def __str__(self, *args, **kwargs):
        import pprint
        return pprint.pformat(dict(self._properties))
       
def combine_indices(arr1, arr2):
    return numpy.union1d(arr1, arr2)

def remove_indices(arr, to_remove):
    return numpy.setdiff1d(arr, to_remove, True)

def index_empty(index):
    return numpy.size(index) == 0 

class ParameterIndexOperationsView(object):
    def __init__(self, param_index_operations, offset, size):
        self._param_index_ops = param_index_operations
        self._offset = offset
        self._size = size
    
    def __getstate__(self):
        return [self._param_index_ops, self._offset, self._size]


    def __setstate__(self, state):
        self._param_index_ops = state[0]
        self._offset = state[1]
        self._size = state[2]


    def _filter_index(self, ind):
        return ind[(ind >= self._offset) * (ind < (self._offset + self._size))] - self._offset


    def iteritems(self):
        for i, ind in self._param_index_ops.iteritems():
            ind2 = self._filter_index(ind)
            if ind2.size > 0:
                yield i, ind2 

    def items(self):
        return [[i,v] for i,v in self.iteritems()]

    def properties(self):
        return [i for i in self.iterproperties()]


    def iterproperties(self):
        for i, _ in self.iteritems():
            yield i 


    def shift(self, start, size):
        raise NotImplementedError, 'Shifting only supported in original ParamIndexOperations'
    

    def clear(self):
        for i, ind in self.items():
            self._param_index_ops.remove(i, ind+self._offset)


    def size(self):
        return reduce(lambda a,b: a+b.size, self.iterindices(), 0)


    def iterindices(self):
        for _, ind in self.iteritems():
            yield ind


    def indices(self):
        [ind for ind in self.iterindices()]


    def properties_for(self, index):
        return vectorize(lambda i: [prop for prop in self.iterproperties() if i in self[prop]], otypes=[list])(index)


    def add(self, prop, indices):
        self._param_index_ops.add(prop, indices+self._offset)


    def remove(self, prop, indices):
        removed = self._param_index_ops.remove(prop, indices+self._offset)
        if removed.size > 0:
            return removed - self._size
        return removed


    def __getitem__(self, prop):
        ind = self._filter_index(self._param_index_ops[prop])
        if ind.size > 0:
            return ind
        raise KeyError, prop
    
    def __str__(self, *args, **kwargs):
        import pprint
        return pprint.pformat(dict(self.iteritems()))

    def update(self, parameter_index_view):
        for i, v in parameter_index_view.iteritems():
            self.add(i, v)
        
    pass

