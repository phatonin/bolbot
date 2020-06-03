'''
Created on Jun 2, 2020

@author: rbossy
'''

import unicodedata
import re

class Ref:
    def __init__(self, value, name=None, auto_ref=None, modifiable=False):
        self.value = value
        self.name = name
        self.auto_ref = auto_ref
        self.modifiable = modifiable
        
    def __str__(self):
        return str(self.value)
    
    def __iadd__(self, other):
        self.value += other
        
    def __isub__(self, other):
        self.value -= other
        
    def is_int(self):
        try:
            int(self.value)
            return True
        except ValueError:
            return False


class Cell:
    def __init__(self, span, text, left=False, right=False, center=False, fillchar=' '):
        self.span = span
        if isinstance(text, Ref):
            self.text = text.value
        else:
            self.text = text
        if self.text is None:
            self.text = '---'
        else:
            self.text = str(self.text)
        self.left = left
        self.right = right
        self.center = center
        self.fillchar = fillchar

    def render(self, width=6):
        w = width * self.span
        if self.left:
            w -= 2
        if self.right:
            w -= 2
        if self.center:
            r = self.text.center(w, self.fillchar)
        else:
            r = self.text.ljust(w, self.fillchar)
        if self.left:
            r = '| ' + r 
        if self.right:
            r += ' |'
        return r

HLine = [Cell(12, '', fillchar='-')]


NON_ALNUM_PATTERN = re.compile('[\W_]+')
def snorm(s):
    spaces = ' '.join(s.split())
    diacritics = ''.join(c for c in unicodedata.normalize('NFKD', spaces) if not unicodedata.combining(c))
    special = NON_ALNUM_PATTERN.sub('', diacritics)
    lower = special.lower()
    return lower

    
    
    
    