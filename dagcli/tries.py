from typing import List

class TrieNode:
    def __init__(self, value, terminal=False, parent=None, data=None):
        self.value = value
        self.terminal = terminal
        self.parent = parent
        self.root = None if not parent else parent.root
        self.count = 0
        self.children = {}
        self.data = data or {}

    def __repr__(self):
        return self.path_to_parent(reduce = lambda a,b: a + "/" + b)

    def add(self, onestr: str):
        self.count += 1
        child = self.children.get(onestr, None)
        if not child:
            child = TrieNode(onestr, False, self)
            self.children[onestr] = child
        return child

    def add_strings(self, strings: List[str], offset=0):
        """ Adds a list of strings from this node and returns the leaf node of the
        bottom most trie node correpsonding to the last string in the string list.
        The terminal flag must be set manually by the caller if needed.
        """
        currnode = self
        child = None
        for off in range(offset, len(strings)):
            currnode = child = currnode.add(strings[off])
        if child: child.count += 1
        return currnode

    def find_leaf(self, strings: List[str], offset=0):
        """ Finds the leaf Trienode that corresponds to the last item in
        the string.
        Usually used to work backwards and other checks.
        """
        currnode = self
        for off in range(offset, len(strings)):
            assert currnode.parent is None or currnode.count > 0, "0 count nodes must be deleted for non root nodes"
            currstr = strings[off]
            child = currnode.children.get(currstr, None)
            if not child:
                return None
            currnode = child
        return currnode

    def remove_string(self, string, offset=0):
        leaf = self.find_leaf(string, offset)
        if leaf: leaf._deccount()
        return leaf is not None

    def path_to_parent(self, reduce=None):
        if not reduce:
            reduce = lambda a,b: a+b
        if self.parent is None:
            return self.value
        return reduce(self.parent.path_to_parent(reduce), self.value)

    def _deccount(self):
        """ Reduces count of a node and if the count reaches 0 removes itself
        from the parent's child list.
        Recursively calls the parent's counter to be decreased.
        """
        self.count -= 1
        if self.count <= 0:
            self.count = 0
            if self.parent:
                # Remove from the parent and reduce its count by one
                del self.parent.children[self.value]
        if self.parent:
            self.parent._deccount()

    def debuginfo(self):
        out = { "terminal": self.terminal, }
        if self.count > 0:
            out["count"] = self.count
        if self.data:
            out["data"] = self.data
        if self.children:
            out["children"] = { k: v.debuginfo() for k,v in self.children.items() }
        return out
