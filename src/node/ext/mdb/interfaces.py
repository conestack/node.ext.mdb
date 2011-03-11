from zope.interface import Attribute
from node.interfaces import INode


class OperationForbidden(Exception): pass


class IRepository(INode):
    """The media database root node.
    """


class IMedia(INode):
    """The media object representation.
    """
    
    mediapath = Attribute(u"List of chars build out of self.__name__, "
                           "representing the relative path to media files.")


class IRevision(INode):
    """Specific media revision.
    """
    
    revisionpath = Attribute(u"Absolute path to the revision without postfix. "
                              "Revision related files append a postfix to this "
                              "path.")


class IMetadata(INode):
    """The Media Metadata.
    """
    
    attributes = Attribute(u"List of allowed metadata attribute names.")
    
    data = Attribute(u"Dictionary containing the metadata.")
    
    metadatapath = Attribute(u"Absolute path to the revision related metadata "
                              "file.")
    
    asxml = Attribute(u"The metadata as XML.")
    
    def initfromfile():
        """This function gets called by Revision.__getitem__ in case that
        metadata already exists for the revision.
        """


class IBinary(INode):
    """The binary data.
    """
    
    payload = Attribute(u"The binary file contents.")
    
    binarypath = Attribute(u"Absolute path to the revision related binary "
                            "file.")
    
    def initfromfile():
        """This function gets called by Revision.__getitem__ in case that
        the binary already exists for the revision.
        """
