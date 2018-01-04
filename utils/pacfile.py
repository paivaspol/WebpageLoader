class Pacfile(object):
    ''' Represents a Pac file. It only generates a string representation of the file. '''
    def __init__(self):
        self.rules = [] # Containing tuple of Pac file condition and return value
        self.default = None
    
    def AddRule(self, condition, retval):
        ''' Adds a run to this pac file. '''
        self.rules.append((condition, retval))
    
    def SetDefaultRule(self, retval):
        ''' Sets the default PAC file rule. '''
        self.default = retval
    
    def __str__(self):
        # Example: 
        #   function FindProxyForURL(url, host) {
        #     if (shExpMatch(url, "*apple-pi.eecs.umich.edu/prefetch*")) { return "DIRECT }
        #     return "PROXY apple-pi.eecs.umich.edu:8080";
        #   }
        retval = 'function FindProxyForURL(url, host) {\n'
        for rule in self.rules:
            retval += 'if ({0}) {{ return "{1}"; }}\n'.format(rule[0], rule[1])
        if self.default is not None:
            retval += 'return "{0}";\n'.format(self.default)
        retval += '}'
        return retval
