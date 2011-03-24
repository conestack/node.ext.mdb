import os
import types
from lxml import etree
from datetime import datetime
from plumber import plumber
from node.locking import locktree
from node.parts import (
    AsAttrAccess,
    NodeChildValidate,
    Adopt,
    Nodespaces,
    Attributes,
    Reference,
    DefaultInit,
    Nodify,
    Lifecycle,
    OdictStorage,
)
from zope.interface import implements
from interfaces import (
    OperationForbidden,
    IRepository,
    IMedia,
    IRevision,
    IMetadata,
    IBinary,
)

try:
    set
except NameError:                                           #pragma NO COVERAGE
    from sets import Set as set                             #pragma NO COVERAGE


def tree(path, indent=0):
    """Print the file system subtree from path below. Debug helper.
    """
    for item in sorted(os.listdir(path)):
        print indent * ' ' + item
        subpath = os.path.join(path, item)
        if os.path.isdir(subpath):
            tree(subpath, indent + 2)


class Base(object):
    __metaclass__ = plumber
    __plumbing__ = (
        AsAttrAccess,
        NodeChildValidate,
        Adopt,
        Nodespaces,
        Attributes,
        Reference,
        DefaultInit,
        Nodify,
        Lifecycle,
        OdictStorage,
    )
    
    @locktree
    def __call__(self):
        for child in self.values():
            child()
    
    @property
    def database(self):
        parent = self.__parent__
        while parent is not None:
            if IRepository.providedBy(parent):
                break
            parent = parent.__parent__
        return parent


class Repository(Base):
    implements(IRepository)
    
    def __init__(self, name=None):
        Base.__init__(self, name=name)
        self._todeletefiles = list()
        self._todeletedirs = list()
    
    @locktree
    def __call__(self):
        if not os.path.exists(self.__name__):
            os.mkdir(self.__name__)
        for path in self._todeletefiles:
            os.remove(path)
        self._todeletefiles = list()
        for directory in self._todeletedirs:
            while directory:
                delete = True
                path = os.path.join(self.root.__name__, *directory)
                childs = os.listdir(path)
                if not childs:
                    os.rmdir(path)
                else:
                    break
                directory.pop()
        self._todeletedirs = list()
        Base.__call__(self)
    
    def __iter__(self):
        if not hasattr(self, '_keys') or not self._keys:
            keys = set()
            self._readkeys(self.__name__, keys)
            self._keys = list(keys)
        for key in self._keys:
            yield key
    
    iterkeys = __iter__
    
    def _readkeys(self, path, keys):
        # should be called as infrequent as possible
        for item in os.listdir(path):
            if os.path.isdir(os.path.join(path, item)):
                self._readkeys(os.path.join(path, item), keys)
            else:
                key = path[len(self.__name__):]
                key = ''.join(key.split(os.path.sep))
                if key:
                    keys.add(key)
        if not os.listdir(path):
            key = path[len(self.__name__):]
            key = ''.join(key.split(os.path.sep))
            if key:
               keys.add(key)
    
    def __getitem__(self, name):
        try:
            return Base.__getitem__(self, name)
        except KeyError, e:
            if not name in self.iterkeys():
                raise KeyError, name
            media = Media()
            self[name] = media
            return Base.__getitem__(self, name)
    
    @locktree
    def __setitem__(self, name, val):
        if not IMedia.providedBy(val):
            raise ValueError, u"Invalid child adding approach."
        if not name in self.iterkeys():
            self._keys.append(name)
        Base.__setitem__(self, name, val)
    
    @locktree
    def __delitem__(self, name):
        media = self[name]
        for key in media.keys():
            del media[key]
        for path in media._todelete:
            self._todeletefiles.append(path)
        self._todeletedirs.append(media.mediapath)
        Base.__delitem__(self, name)
        self._keys = None


class MediaKeys(object):
    
    def __init__(self, path):
        self.path = os.path.join(path, 'database.keys')
        if not os.path.exists(self.path):
            with open(self.path, 'w') as file:
                file.write('')
    
    def dump(self, next):
        with open(self.path, 'a') as file:
            file.write('%s\n' % next)
    
    def next(self):
        lines = None
        with open(self.path, 'r') as file:
            lines = [line.strip('\n') for line in file.readlines()]
        if not lines:
            return self._next_key()
        return self._next_key(lines[-1])
    
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    
    def _next_key(self, last=None):
        if last is None:
            return self.chars[0]
        last = list(last)
        last.reverse()
        next = [_ for _ in last]
        pt = 0
        length = len(last)
        for i in range(length):
            index = self.chars.find(last[i])
            nextchar = index == len(self.chars) - 1
            keyends = i + 1 == length
            if nextchar and keyends:
                return (length + 1) * self.chars[0]
            elif nextchar:
                next[i] = self.chars[0]
            else:
                next[i] = self.chars[index + 1]
                break
        next.reverse()
        return ''.join(next)


class Media(Base):
    implements(IMedia)
    
    def __init__(self, name=None):
        Base.__init__(self, name=name)
        self._todelete = list()
    
    @property
    def mediapath(self):
        return [c for c in self.__name__]
    
    @locktree
    def __call__(self):
        if self.database is None:
            raise OperationForbidden(u"Media not contained in a Database.")
        for path in self._todelete:
            os.remove(path)
        self._todelete = list()
        path = self.root.__name__
        for char in self.mediapath:
            path = os.path.join(path, char)
            if not os.path.exists(path):
                os.mkdir(path)
        Base.__call__(self)
    
    def __iter__(self):
        keys = set()
        for key in Base.__iter__(self):
            keys.add(key)
        path = os.path.join(self.root.__name__, *self.mediapath)
        if os.path.exists(path):
            for item in os.listdir(path):
                if (item.endswith('.binary') \
                  or item.endswith('.metadata')) \
                  and not os.path.join(path, item) in self._todelete:
                    keys.add(item[:item.rfind('.')])
        for key in keys:
            yield key
    
    iterkeys = __iter__
    
    def __getitem__(self, name):
        if not name in self.iterkeys():
            raise KeyError, name
        try:
            revision = Base.__getitem__(self, name)
        except KeyError, e:
            revision = Revision()
            self[name] = revision
        return Base.__getitem__(self, name)
    
    @locktree
    def __setitem__(self, name, val):
        if not IRevision.providedBy(val):
            raise ValueError, u"Invalid child adding approach."
        Base.__setitem__(self, name, val)
    
    @locktree
    def __delitem__(self, name):
        if not name in self:
            raise KeyError(name)
        rev = self[name]
        for key in ['metadata', 'binary']:
            if key in rev:
                del rev[key]
        for path in rev._todelete:
            self._todelete.append(path)
        Base.__delitem__(self, name)


class Revision(Base):
    implements(IRevision)
    
    def __init__(self, name=None):
        Base.__init__(self, name=name)
        self._todelete = list()
    
    @property
    def revisionpath(self):
        relativerevpath = self.__parent__.mediapath + [self.__name__]
        return os.path.join(self.root.__name__, *relativerevpath)
    
    @locktree
    def __call__(self):
        if self.database is None:
            raise OperationForbidden(u"Revision not contained in a Media.")
        for path in self._todelete:
            os.remove(path)
        self._todelete = list()
        Base.__call__(self)
    
    @locktree
    def __setitem__(self, name, val):
        if IMetadata.providedBy(val):
            Base.__setitem__(self, 'metadata', val)
            return
        if IBinary.providedBy(val):
            Base.__setitem__(self, 'binary', val)
            return
        raise ValueError, u"Invalid child adding approach."
    
    @locktree
    def __delitem__(self, name):
        if not name in ['binary', 'metadata']:
            raise KeyError(name)
        path = '%s.%s' % (self.revisionpath, name)
        Base.__delitem__(self, name)
        if os.path.exists(path):
            self._todelete.append(path)
        
    def __iter__(self):
        for name in ['metadata', 'binary']:
            in_mem = name in self.storage.iterkeys()
            path = '%s.%s' % (self.revisionpath, name)
            if (in_mem or os.path.exists(path)) and not path in self._todelete:
                yield name
    
    iterkeys = __iter__
    
    def __getitem__(self, name):
        if not name in ['metadata', 'binary']:
            raise KeyError, name
        try:
            revision = Base.__getitem__(self, name)
        except KeyError, e:
            factory = {
                'metadata': Metadata,
                'binary': Binary,
            }
            if os.path.exists('%s.%s' % (self.revisionpath, name)):
                node = factory[name]()
                self[name] = node
                node.initfromfile()
            else:
                raise KeyError, name
        return Base.__getitem__(self, name)


class Metadata(Base):
    implements(IMetadata)
    
    # The allowed attributes for metadata.
    # XXX: configurable
    attributes = [
        '_uid_',
        '_author_',
        '_created_',
        '_effective_',
        '_expires_',
        '_revision_',
        '_mimetype_',
        '_creator_',
        '_keywords_',
        '_suid_',
        '_relations_',
        '_title_',
        '_description_',
        '_alttag_',
        '_body_',
        '_state_',
        '_relations_',
        '_keywords_',
        '_visibility_',
        '_modified_',
        '_filename_',
    ]
    
    def __init__(self, name=None, data=None):
        Base.__init__(self)
        self.data = dict()
        if data:
            self.data.update(data)
    
    @locktree
    def __call__(self):
        if self.database is None:
            raise OperationForbidden(u"Metadata not contained in a Revision.")
        file = open(self.metadatapath, 'w')
        file.write(self.asxml)
        file.close()
    
    def __setattr__(self, name, value):
        if '_%s_' % name in self.attributes:
            self.data['_%s_' % name] = value
        else:
            Base.__setattr__(self, name, value)
    
    def __getattr__(self, name):
        if '_%s_' % name in object.__getattribute__(self, 'attributes'):
            return object.__getattribute__(self, 'data').get('_%s_' % name)
        return object.__getattribute__(self, name)
    
    @locktree
    def __delitem__(self, name):
        if '_%s_' % name in self.data:
            del self.data['_%s_' % name]
        else:
            raise KeyError(u"metadata %s does not exist" % name)
    
    def get(self, name, default=None):
        return self.data.get('_%s_' % name, default)
    
    def keys(self):
        return [k.strip('_') for k in self.data.keys()]
    
    @property
    def metadatapath(self):
        return '%s.%s' % (self.__parent__.revisionpath, 'metadata')
    
    @property
    def asxml(self):
        root = etree.Element('metadata')
        for key, value in self.data.items():
            sub = etree.SubElement(root, key.strip('_'))
            if type(value) in [types.ListType, types.TupleType]:
                for item in value:
                    subsub = etree.SubElement(sub, 'item')
                    subsub.text = self._w_value(item)
            else:
                sub.text = self._w_value(value)
        return etree.tostring(root, pretty_print=True)
    
    def initfromfile(self):
        """Initialize metadata attributes from existing file. Ignores all
        keys already defined on self.data
        """
        if not self.__parent__ or not os.path.exists(self.metadatapath):
            return
        file = open(self.metadatapath, 'r')
        tree = etree.parse(file)
        file.close()
        root = tree.getroot()
        for elem in root.getchildren():
            children = elem.getchildren()
            if children:
                val = list()
                for subelem in children:
                    value = subelem.text
                    if value is None:
                        value = ''
                    val.append(self._r_value(value.strip()))
                self.data['_%s_' % elem.tag] = val
            else:
                value = elem.text
                if value is None:
                    value = ''
                self.data['_%s_' % elem.tag] = self._r_value(value.strip())
        file.close()
    
    def _w_value(self, val):
        if isinstance(val, datetime):
            return self._dt_to_iso(val)
        if not isinstance(val, unicode):
            val = val.decode('utf-8')
        return val
    
    def _r_value(self, val):
        try:
            return self._dt_from_iso(val)
        except ValueError:
            if not isinstance(val, unicode):
                val = str(val).decode('utf-8')
            return val
    
    def _dt_from_iso(self, str):
        return datetime.strptime(str, '%Y-%m-%dT%H:%M:%S')
    
    def _dt_to_iso(self, dt):
        iso = dt.isoformat()
        if iso.find('.') != -1:
            iso = iso[:iso.rfind('.')]
        return iso


class Binary(Base):
    implements(IBinary)
    
    def __init__(self, name=None, payload=None):
        Base.__init__(self)
        self.payload = payload
    
    @locktree
    def __call__(self):
        if self.database is None:
            raise OperationForbidden(u"Binary not contained in a Revision.")
        file = open(self.binarypath, 'w')
        payload = self.payload and self.payload or ''
        file.write(payload)
        file.close()
    
    @locktree
    def __delitem__(self, name):
        raise OperationForbidden(u"%s does not support this operation" % \
                                 self.__class__.__name__)
    
    @property
    def binarypath(self):
        return '%s.%s' % (self.__parent__.revisionpath, 'binary')
    
    def initfromfile(self):
        """Initialize self.payload from existing file if existing and not set
        yet.
        """
        if not self.__parent__ \
          or not os.path.exists(self.binarypath) \
          or self.payload is not None:
            return
        file = open(self.binarypath, 'rb')
        self.payload = file.read()
        file.close()
