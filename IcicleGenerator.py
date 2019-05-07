bl_info = {"name":"Icicle Generator",
           "author":"Eoin Brennan (Mayeoin Bread)",
           "version":(2,3),
           "blender":(2,7,9),
           "location":"View3D > Add > Mesh",
           "description":"Adds a linear string of icicles of different sizes",
           "warning":"",
           "wiki_url":"",
           "tracker_url":"",
           "category":"Add Mesh" }

# F8 to remove "dead" scripts

import bpy
import bmesh
from mathutils import Vector, Matrix
from math import pi, sin, cos, atan
from bpy.props import FloatProperty, IntProperty, BoolProperty
import random

class IcicleGenerator(bpy.types.Operator):
    """Icicle Generator"""
    bl_idname = "mesh.icicle_gen"
    bl_label = "Icicle Generator"
    bl_options = {"REGISTER", "UNDO"}
    
    ##
    # User input
    ##
    
    # Maximum radius
    maxR = FloatProperty(
        name="Max Radius",
        description="Maximum radius of a cone",
        default=0.15,
        min=0.01,
        max=1.0,
        unit="LENGTH")
    # Minimum radius
    minR = FloatProperty(
        name="Min Radius",
        description="Minimum radius of a cone",
        default=0.025,
        min=0.01,
        max=1.0,
        unit="LENGTH")
    # Maximum depth
    maxD = FloatProperty(
        name="Max Depth",
        description="Maximum depth (height) of cone",
        default=2.0,
        min=0.2,
        max=2.0,
        unit="LENGTH")
    # Minimum depth
    minD = FloatProperty(
        name="Min Depth",
        description="Minimum depth (height) of cone",
        default=1.5,
        min=0.2,
        max=2.0,
        unit="LENGTH")
    # Number of verts at base of cone
    verts = IntProperty(
        name="Vertices",
        description="Number of vertices",
        default=8,
        min=3,
        max=24)
    # Select base mesh at end
    # Range of subdivides for vertical edges, these will be scaled and shifted to create some randomness
    subdivs = IntProperty(
        name="Subdivides",
        description="Number of subdivides",
        default=3,
        min=0,
        max=8)
    # Number of iterations before giving up trying to add cones
    # Prevents crashes and (long-term) freezes
    # Obviously, the more iterations, the more time spent calculating.
    # Max value (10,000) is safe but can be slow,
    # 2000 to 5000 should be adequate for 95% of cases
    its = IntProperty(
        name="Iterations",
        description="Number of iterations before giving up, prevents freezing/crashing",
        default=2000,
        min=1,
        max=10000)
    # Re-selects the initial selection after adding icicles
    rese = BoolProperty(
        name="Reselect base mesh",
        description="Re-select the base mesh after adding icicles",
        default=True)
    
    ##
    # Main function
    ##
    def execute(self, context):
        rad = self.maxR
        radM = self.minR
        depth = self.maxD
        minD = self.minD

        def pos_neg():
            return -1 if random.random() < 0.5 else 1
        
        ##
        # Add cone function
        ##
        def add_cone(v_co,randrad,rd):
            bpy.ops.mesh.primitive_cone_add(
                vertices = self.verts,
                radius1 = randrad,
                radius2 = 0.0,
                depth = rd,
                end_fill_type = 'NGON',
                view_align = False,
                # Adjust the Z-height to account for the depth of the cone
                # As pivot point is in the centre of the mesh
                location = (v_co.x, v_co.y, v_co.z - rd/2),
                rotation = (pi, 0.0, 0.0))
        
        ##
        # Add icicle function
        ##
        def add_icicles(rad, radM, depth, minD):
            obj = bpy.context.object
            bm = bmesh.from_edit_mesh(obj.data)
            wm = obj.matrix_world
            
            # Get the verts by checking the selected edge
            edge_verts = [v for v in bm.verts if v.select]
            # Make sure we only have 2 verts to use
            if len(edge_verts) != 2:
                print('Incorrect number of verts selected. Expected 2, found ' + str(len(edge_verts)))
                return
            
            # vertex coordinates
            v1 = edge_verts[0].co
            v2 = edge_verts[1].co
            # World matrix for positioning
            pos1 = wm * v1
            pos2 = wm * v2
            vm = pos1 - pos2
            
            # current length
            l = 0.0
            # Total length of current edge
            t_length = ((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2 + (pos1.z - pos2.z)**2)**0.5
            
            # Equal values, therfore radius should be that size
            # Otherwise randomise it
            randrad = rad if radM==rad else (rad-radM)*random.random()
            # Depth, as with radius above
            rd = depth if depth==minD else (depth-minD)*random.random()
            # Get user iterations
            iterations = self.its
            # Counter for iterations
            c = 0
            
            # Check if we're working on vertical lines here,
            # As we don't deal with them
            if pos1.x == pos2.x and pos1.y == pos2.y:
                print("Cannot work on vertical lines")
                return

            while l < t_length and c < iterations:
                rr = randrad if radM==rad else randrad+radM
                dd = rd if depth==minD else rd+minD
                numCuts = random.randint(0, self.subdivs)
                
                # Check depth is bigger then radius
                # Icicles generally longer than wider
                if dd > rr:
                    # Check that we won't overshoot the length of the line
                    # By using a cone of this radius
                    if l+rr+rr <= t_length:
                        l += rr
                        t_co = pos2 + (l/t_length) * vm
                        add_cone(t_co, rr, dd)
                        # Add on the other half of the radius
                        l += rr
                        # Set up a random variable to offset the subdivisions on the icicle if added
                        t_rand = rr * random.random() * pos_neg()
                        # Check that we're going to subdivide, and that we're going to shift them a noticable amount
                        if numCuts > 0 and abs(t_rand) > 0.02:
                            bm.edges.ensure_lookup_table()
                            coneEdges = [e for e in bm.edges if e.select == True]
                            # Get the vertical edges only so we can subdivide
                            verticalEdges = [e for e in coneEdges if e.verts[0].co.z != e.verts[1].co.z]
                            ret = bmesh.ops.subdivide_edges(bm, edges=verticalEdges, cuts=numCuts)
                            # Get the newly-generated verts so we can shift them
                            new_verts = [v for v in ret['geom_split'] if type(v) is bmesh.types.BMVert]
                            for t in range(numCuts):
                                v_z = new_verts[0].co.z
                                # add buffer of +/- 0.02 in case vert height isn't exactly exact
                                loop_verts = [v for v in new_verts if -0.02 < v.co.z - v_z < 0.02]
                                bpy.ops.mesh.select_all(action='DESELECT')
                                for v in loop_verts:
                                    new_verts.pop(new_verts.index(v))
                                    v.select = True
                                bpy.ops.transform.translate(value=(t_rand, t_rand, t_rand))
                                # Generate new t_rand value, and (try) make it less effective as we go down the icicle
                                t_rand = t_rand * random.random() * pos_neg() * (1-t)/numCuts
                            obj.data.update()
                
                randrad = rad if radM==rad else (rad-radM)*random.random()
                rd = depth if depth==minD else (depth-minD)*random.random()
                
                c += 1
                if c >= iterations:
                    print("Maximum iterations reached on edge")

        ##
        # Run function
        ##        
        def runIt(rad, radM, depth, minD):
            # Check that min values are less than max values
            if(rad >= radM) and (depth >= minD):
                obj = bpy.context.object
                # have this so that it works on every edge in the object (instead of old selection)
                ogMode = obj.mode
                if obj.mode != 'EDIT':
                    bpy.ops.object.mode_set(mode='EDIT')
                
                bm = bmesh.from_edit_mesh(obj.data)
                oEdge = [e for e in bm.edges]
                
                for e in oEdge:
                    bpy.ops.mesh.select_all(action='DESELECT')
                    bm.edges.ensure_lookup_table()
                    e.select = True
                    add_icicles(rad, radM, depth, minD)
                
                if self.rese:
                    bpy.ops.mesh.select_all(action='DESELECT')
                    bm.edges.ensure_lookup_table()
                    for e in oEdge:
                        e.select = True
                
                if ogMode != 'EDIT':
                    bpy.ops.object.mode_set(mode=ogMode)

        # Run the function
        obj = bpy.context.object
        if obj == None:
            print("No object selected")
        elif obj.type == 'MESH':
            runIt(rad, radM, depth, minD)
        else:
            print("Only works on meshes")
        return {'FINISHED'}

# Add to menu and register/unregister stuff
def menu_func(self, context):
    self.layout.operator(IcicleGenerator.bl_idname,text="Icicle", icon="PLUGIN")

def register():
    bpy.utils.register_class(IcicleGenerator)
    bpy.types.INFO_MT_mesh_add.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(IcicleGenerator)
    bpy.types.INFO_MT_mesh_add.remove(menu_func)
    
if __name__ == "__main__":
    register()