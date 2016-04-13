#
# Copyright 2014, NICTA
#
# This software may be distributed and modified according to the terms of
# the BSD 2-Clause license. Note that NO WARRANTY is provided.
# See "LICENSE_BSD2.txt" for details.
#
# @TAG(NICTA_BSD)
#

"""
Various internal utility functions. Pay no mind to this file.
"""

from __future__ import absolute_import, division, print_function, \
    unicode_literals



from .Object import seL4_IA32_4M, seL4_IA32_4K, seL4_ARM_SectionObject, \
    seL4_ARM_SuperSectionObject, seL4_ARM_SmallPageObject, seL4_ARM_LargePageObject, \
    seL4_IA32_PageDirectoryObject, seL4_IA32_PageTableObject, \
    seL4_ARM_PageDirectoryObject, seL4_ARM_PageTableObject, \
    PageTable, PageDirectory

# Size of a frame and page (applies to all architectures)
FRAME_SIZE = 4096 # bytes
PAGE_SIZE = 4096 # bytes

SIZE_4GB = 4 * 1024 * 1024 * 1024
SIZE_32M = 32 * 1024 * 1024
SIZE_16M = 16 * 1024 * 1024
SIZE_4M = 4 * 1024 * 1024
SIZE_2M = 2 * 1024 * 1024
SIZE_1M = 1024 * 1024
SIZE_64K = 64 * 1024

class Frame:
    def __init__(self, size, object):
        self._size = size
        self._object = object
    @property
    def size(self):
        return self._size
    @property
    def object(self):
        return self._object

class Level:
    """
    Abstraction of a 'level' in a virtual address space hierarchy. A level
    is parameterized by things such as; the virtual address range covered
    by this object, the virtual address range covered by each entry in
    the level and what kinds of frames (if any) can be placed directly
    at this level.
    """
    def __init__(self, coverage, pages, object, make_object, type_name, parent = None, child = None):
        self.coverage = coverage
        self.pages = pages
        self.parent = parent
        self.child = child
        self.object = object
        self.make_object = make_object
        self.type_name = type_name
    def base_vaddr(self, vaddr):
        """
        Base address of the range covered by this level, determined
        by using a virtual address from somewhere inside this object
        """
        return round_down(vaddr, self.coverage)
    def parent_index(self, vaddr):
        """
        Index of this object in the parent level. Determine by a
        using a virtual address from inside this object
        """
        return self.parent.child_index(vaddr)
    def child_index(self, vaddr):
        """
        Index of a child object that is contained in this object.
        Determine the index by using a combination of our coverage
        and coverage of child objects. If we have no child assume
        our 'child' is a standard page
        """
        if self.child is None:
            return vaddr % self.coverage // PAGE_SIZE
        else:
            return vaddr % self.coverage // self.child.coverage

def make_levels(levels):
    assert levels is not None
    assert len(levels) > 0
    for i in xrange(0, len(levels), 1):
        if i > 0:
            levels[i].parent = levels[i - 1]
        if i < len(levels) - 1:
            levels[i].child = levels[i + 1]
    return levels[0]

class Arch:
    def get_pages(self):
        level = self.vspace()
        pages = []
        while level is not None:
            pages.extend(level.pages)
            level = level.child
        return pages

class IA32Arch(Arch):
    def capdl_name(self):
        return "ia32"
    def vspace(self):
        return make_levels([
            Level(SIZE_4GB, [Frame(SIZE_4M, seL4_IA32_4M)], seL4_IA32_PageDirectoryObject, PageDirectory, "pd"),
            Level(SIZE_4M, [Frame(PAGE_SIZE, seL4_IA32_4K)], seL4_IA32_PageTableObject, PageTable, "pt"),
        ])
    def word_size_bits(self):
        return 32

class ARM32Arch(Arch):
    def capdl_name(self):
        return "arm11"
    def vspace(self):
        return make_levels([
            Level(SIZE_4GB, [Frame(SIZE_1M, seL4_ARM_SectionObject), Frame(SIZE_16M, seL4_ARM_SuperSectionObject)], seL4_ARM_PageDirectoryObject, PageDirectory, "pd"),
            Level(SIZE_1M, [Frame(PAGE_SIZE, seL4_ARM_SmallPageObject), Frame(SIZE_64K, seL4_ARM_LargePageObject)], seL4_ARM_PageTableObject, PageTable, "pt"),
        ])
    def word_size_bits(self):
        return 32

class ARMHypArch(Arch):
    def capdl_name(self):
        return "arm11"
    def vspace(self):
        return make_levels([
            Level(SIZE_4GB, [Frame(SIZE_2M, seL4_ARM_SectionObject), Frame(SIZE_32M, seL4_ARM_SuperSectionObject)], seL4_ARM_PageDirectoryObject, PageDirectory, "pd"),
            Level(SIZE_2M, [Frame(PAGE_SIZE, seL4_ARM_SmallPageObject), Frame(SIZE_64K, seL4_ARM_LargePageObject)], seL4_ARM_PageTableObject, PageTable, "pt"),
        ])
    def word_size_bits(self):
        return 32

def lookup_architecture(arch):
    normalise = {
        'aarch32':'aarch32',
        'arm':'aarch32',
        'arm11':'aarch32',
        'arm_hyp':'arm_hyp',
        'ia32':'ia32',
        'x86':'ia32',
    }
    arch_map = {
        'aarch32': ARM32Arch(),
        'arm_hyp': ARMHypArch(),
        'ia32': IA32Arch(),
    }
    try:
        return arch_map[normalise[arch.lower()]]
    except KeyError:
        raise Exception('invalid architecture: %s' % arch)

def normalise_architecture(arch):
    return lookup_architecture(arch).capdl_name()

def round_down(n, alignment=FRAME_SIZE):
    """
    Round a number down to 'alignment'.
    """
    return n // alignment * alignment

def last_level(level):
    while level.child is not None:
        level = level.child
    return level

def page_sizes(arch):
    list = [page.size for page in lookup_architecture(arch).get_pages()]
    list.sort()
    return list

def page_table_coverage(arch):
    """
    The number of bytes a page table covers.
    """
    return last_level(lookup_architecture(arch).vspace()).coverage

def page_table_vaddr(arch, vaddr):
    """
    The base virtual address of a page table, derived from the virtual address
    of a location within that table's coverage.
    """
    return last_level(lookup_architecture(arch).vspace()).base_vaddr(vaddr)

def page_table_index(arch, vaddr):
    """
    The index of a page table within a containing page directory, derived from
    the virtual address of a location within that table's coverage.
    """
    return last_level(lookup_architecture(arch).vspace()).parent_index(vaddr)

def page_index(arch, vaddr):
    """
    The index of a page within a containing page table, derived from the
    virtual address of a location within that page.
    """
    return last_level(lookup_architecture(arch).vspace()).child_index(vaddr)

def page_vaddr(vaddr):
    """
    The base virtual address of a page, derived from the virtual address of a
    location within that page.
    """
    return vaddr // PAGE_SIZE * PAGE_SIZE
