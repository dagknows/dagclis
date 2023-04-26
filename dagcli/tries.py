from typing import List

class TrieNode:
    def __init__(self, value, terminal=False, parent=None, data=None):
        self.value = value
        self.terminal = terminal
        self.parent = parent
        self.count = 0
        self.data = data or {}
        self.children = {}

        # Children match explicit/literal values.
        # Every node can dedicate "one" extra child to a param
        # This itself is the start of a trie if a param has matched
        # This is great for trees like:
        # Root -> collection1 -> create
        # Root -> collection1 -> list
        # Root -> collection1 -> <id> -> details
        # Root -> collection1 -> <id> -> update
        # Root -> collection1 -> <id> -> execs -> create
        #
        # Here the collection1 node would have a 2 children - "create" and "list"
        # and a param child - "id" which would match "anything else" other than static
        # children.  We can extend this idea to have multiple param trie children to
        # suit different arities.
        # eg param1 <id1> <id2> get
        # eg param1 <id1> create
        # 
        # Here ID 1 would have a trie node as its child
        self.param_trie = None
        self._is_param_node = False

    @property
    def is_param_node(self):
        return self._is_param_node

    @property
    def root(self):
        if self.parent == None: return self
        else: return self.parent.root

    def __repr__(self):
        return self.path_to_root(reduce = lambda a,b: a + "/" + b)

    def add(self, onestr: str, as_param=False):
        self.count += 1
        if as_param:
            if self.param_trie:
                # At this point we already have a param
                # Since params of all names are the "same" we can accept this as is
                # What needs to be done is the bound variable needs to be set correctly
                # because books/{book_id}/pages and books/{book.id}/pages/delete are the same
                # They just set some variable that is decided by the pages or /pages/delete
                # handler - it can do this by using a lexical distance of bindings instead
                # of names
                return self.param_trie
            else:
                child = TrieNode(onestr, False, self)
                child._is_param_node = True
                self.param_trie = child
            return self.param_trie
        else:
            child = self.children.get(onestr, None)
            if not child:
                # we are good to add a child
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

    def path_to_ancestor(self, node=None, reduce=None):
        if not reduce:
            reduce = lambda a,b: a+b
        if self.parent is None:
            return self.value
        elif node == self:
            return self.value
        return reduce(self.parent.path_to_ancestor(node, reduce), self.value)

    def path_to_root(self, reduce=None):
        return self.path_to_ancestor(None, reduce)

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
