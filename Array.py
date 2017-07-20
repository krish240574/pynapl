# -*- coding: utf-8 -*-


import operator
import json
import codecs

from Util import *

# assuming ⎕IO=0 for now
class APLArray(object):
    """Serializable multidimensional array.
      
    Every element of the array must be either a value or another array. 
    """
    
    TYPE_HINT_NUM = 0
    TYPE_HINT_CHAR = 1

    # json decoder object hook
    def __json_object_hook(jsobj):
        # if this is an APL array, return it as such
        
        if type(jsobj) is dict \
        and 'r' in jsobj \
        and 'd' in jsobj:
            type_hint = APLArray.TYPE_HINT_NUM
            if 't' in jsobj: type_hint = jsobj['t']
            return APLArray(jsobj['r'], list(jsobj['d']), type_hint=type_hint)

        else:
            return jsobj
    
    # define a reusable json decoder
    __json_decoder = json.JSONDecoder(encoding="utf8", object_hook=__json_object_hook)

    @staticmethod
    def from_python(obj, enclose=True):
        # lists, tuples and strings can be represented as vectors
        if type(obj) in (list,tuple):
            return APLArray(rho=[len(obj)], 
                            data=[APLArray.from_python(x,enclose=False) for x in obj])
        
        # numbers can be represented as numbers, enclosed if at the upper level so we always send an 'array'
        elif type(obj) in (int,long,float): # complex not supported for now
            if enclose: return APLArray(rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_NUM)
            else: return obj

        # a one-element string is a character, a multi-element string is a vector
        elif type(obj) in (str,unicode):
            if len(obj) == 1:
                if enclose: return APLArray(rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_CHAR)
                else: return obj
            else:
                aplstr = APLArray.from_python(list(obj))
                aplstr.type_hint = APLArray.TYPE_HINT_CHAR

        # nothing else is supported for now
        raise TypeError("type not supported: " + repr(type(obj)))

    def genTypeHint(self):
        if not self.type_hint is None:
            # it already exists
            return self.type_hint
        elif len(data)!=0:
            # we have some data to use
            if isinstance(data[0], APLArray):
                return data[0].getTypeHint()
            elif type(data[0]) in (str,unicode):
                return APLArray.TYPE_HINT_CHAR
            else:
                return APLArray.TYPE_HINT_NUM
        else:
            # if we can't deduce anything, assume numeric empty vector
            return APLArray.TYPE_HINT_NUM
            

    def __init__(self, rho, data, type_hint=None):
        self.rho=rho
        self.data=extend(data, product(rho))
        # deduce type from data
        if not type_hint is None:
            # hint is given
            self.type_hint = type_hint
        else:
            self.type_hint = self.genTypeHint()

    def flatten_idx(self, idx, IO=0):
        return sum((x-IO)*(y-IO) for x,y in zip(scan_reverse(operator.__mul__,self.rho[1:]+[1]), idx))

    def check_valid_idx(self, idx):
        if not len(idx)==len(self.rho):
            raise IndexError("⍴=%d, should be %d"%len(self.rho),len(idx))
        
        if not all(0 <= ix < sz for (ix,sz) in zip(idx, self.rho)):
            raise IndexError()


    def __getitem__(self,idx):
        self.check_valid_idx(idx)
        return self.data[self.flatten_idx(idx)]

    def __setitem__(self,idx,val):
        self.check_valid_idx(idx)
        self.data[self.flatten_idx(idx)]=val

    def toJSONString(self):
        return json.dumps(self, cls=ArrayEncoder, ensure_ascii=False)

    @staticmethod 
    def fromJSONString(string):
        return APLArray.__json_decoder.decode(string)

# serialize an array using JSON
class ArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, APLArray):
            return {"r": obj.rho, "d": obj.data, "t":obj.genTypeHint()}
        else:
            return json.JSONEncoder.default(obj)
