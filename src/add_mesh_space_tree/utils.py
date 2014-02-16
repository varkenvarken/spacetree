from os.path import exists, join
import bpy

def load_material(library, material_name):
    """given a path to a library .blend file and the name of a material, append that material and reurn a reference to it.
    
    Note that the name of the material may change if a material with the same name is already present.
    """
    before = set(m.name for m in bpy.data.materials)
    with bpy.data.libraries.load(library) as (data_from, data_to):
        # even though the next line looks like an assignment, linked materials are added, nothing is overwritten
        data_to.materials = [m for m in data_from.materials if m == material_name]
    after = set(m.name for m in bpy.data.materials)
    # this whole business seems necessary because appending materials happens in an arbitrary order and names may change.
    # by adding a single material and comparing the sets of material names before and after appending, we learn the name of
    # the newly added material.
    new = after - before
    if len(new) != 1:
        raise ValueError("While loading material %s from library %s %d materials were found (%s) instead of just 1"%(
            material_name,library,len(new),str(new)))
    return bpy.data.materials[new.pop()]
    
def load_material_from_bundled_lib(script_name, library, material_name):
    """Load a material froom a library located in the installation directory of a script.""" 
    for dir in ('addons','addons_contrib'):
        for path in bpy.utils.script_paths():
            fullpath = join(path, dir, script_name, library)
            if exists(fullpath):
                return load_material(fullpath, material_name)
    return None

def get_vertex_group(context, name):
    """Get a reference to the named vertex group of the active object, creating it if necessary."""
    ob = context.active_object
    if ob is None :
        return None
    if name in ob.vertex_groups:
        return ob.vertex_groups[name]
    else:
        bpy.ops.object.vertex_group_add()
        vg = ob.vertex_groups.active
        vg.name = name
        return vg
 