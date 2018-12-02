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
    maxR = FloatProperty(name="Max Radius",
        description="Maximum radius of a cone",
        default=0.15,
        min=0.01,
        max=1.0,
        unit="LENGTH")
    # Minimum radius
    minR = FloatProperty(name="Min Radius",
        description="Minimum radius of a cone",
        default=0.025,
        min=0.01,
        max=1.0,
        unit="LENGTH")
    # Maximum depth
    maxD = FloatProperty(name="Max Depth",
        description="Maximum depth (height) of cone",
        default=2.0,
        min=0.2,
        max=2.0,
        unit="LENGTH")
    # Minimum depth
    minD = FloatProperty(name="Min Depth",
        description="Minimum depth (height) of cone",
        default=1.5,
        min=0.2,
        max=2.0,
        unit="LENGTH")
    # Number of verts at base of cone
    verts = IntProperty(name="Vertices", description="Number of vertices", default=8, min=3, max=24)
    # Select base mesh at end
    # Range of subdivides for vertical edges, these will be scaled and shifted to create some randomness
    subdivs = IntProperty(name="Subdivides", description="Number of subdivides", default=3, min=0, max=8)
    # Number of iterations before giving up trying to add cones
    # Prevents crashes and freezes
    # Obviously, the more iterations, the more time spent calculating.
    # Max value (10,000) is safe but can be slow,
    # 2000 to 5000 should be adequate for 95% of cases
    its = IntProperty(name="Iterations", description="Number of iterations before giving up, prevents freezing/crashing", default=2000, min=1, max=10000)
    # Re-selects the initial selection after adding icicles
    rese = BoolProperty(name="Reselect base mesh", description="Re-select the base mesh after adding icicles", default=True)
    
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
        def add_cone(x,y,z,randrad,rd):
            # TODO subdivide (vetically) and scale/offset loops to create more jagged icicles
            bpy.ops.mesh.primitive_cone_add(
                vertices = self.verts,
                radius1 = randrad,
                radius2 = 0.0,
                depth = rd,
                end_fill_type = 'NGON',
                view_align = False,
                location = (x,y,z),
                rotation = (pi, 0.0, 0.0))
        ##
        # Get average of selected verts
        ##
        def get_average(sel_verts):
            med = Vector()
            for v in sel_verts:
                med = med + v.co
            return med / len(sel_verts)
        
        ##
        # Add icicle function
        ##
        def add_icicles(rad, radM, depth, minD):
            pos1 = pos2 = Vector((0.0,0.0,0.0))
            pos = 0
            obj = bpy.context.object
            bm = bmesh.from_edit_mesh(obj.data)
            wm = obj.matrix_world
            # Vectors for selected verts
            for v in bm.verts:
                if v.select:
                    if pos == 0:
                        p1 = v.co
                        pos = 1
                    elif pos == 1:
                        p2 = v.co
                        pos = 2
                    else:
                        p5 = v.co
            # Set first to left most vert on X-axis...
            if(p1.x > p2.x):
                pos1 = p2
                pos2 = p1
            # Or bottom-most on Y-axis if X-axis not used
            elif(p1.x == p2.x):
                [pos1, pos2] = [p2,p1] if p1.y>p2.y else [p1,p2]
            else:
                pos1 = p1
                pos2 = p2
            # World matrix for positioning
            pos1 = wm * pos1
            pos2 = wm * pos2
            
            # X values not equal, working on X-Y-Z planes
            if pos1.x != pos2.x:
                xEqual = False
                #Get the angle of the line
                angle = atan((pos2.x-pos1.x)/(pos2.y-pos1.y)) if pos2.y!=pos1.y else pi/2
                # Total length of line, neglect Z-value (Z only affects height)
                xLength = (((pos2.x-pos1.x)**2)+((pos2.y-pos1.y)**2))**0.5
                # Slopes of lines
                ySlope = (pos2.y-pos1.y)/(pos2.x-pos1.x)
                zSlope = (pos2.z-pos1.z)/(pos2.x-pos1.x)
                # Fixes positioning error with some angles
                i = pos2.x if angle<0 else pos1.x
                j = pos2.y if angle<0 else pos1.y
                k = pos2.z if angle<0 else pos1.z
                l = 0.0
                
                # Z and Y axis' intercepts
                zInt = k - (zSlope*i)
                yInt = j - (ySlope*i)
            elif (pos1.x == pos2.x) and (pos1.y != pos2.y):
                xEqual = True
                xLength = ((pos2.y-pos1.y)**2)**0.5
                i = pos1.x
                j = pos1.y
                k = pos1.z
                l = 0.0

                zSlope = (pos2.z-pos1.z)/(pos2.y-pos1.y)
                zInt = k - (zSlope*j)
            else:
                print("Cannot work on vertical lines")
                return
            
            # Equal values, therfore radius should be that size
            # Otherwise randomise it
            randrad = rad if radM==rad else (rad-radM)*random.random()
            # Depth, as with radius above
            rd = depth if depth==minD else (depth-minD)*random.random()
            # Get user iterations
            iterations = self.its
            # Counter for iterations
            c = 0

            while l < xLength and c < iterations:
                rr = randrad if radM==rad else randrad+radM
                dd = rd if depth==minD else rd+minD
                #numCuts = random.randint(1,5)
                numCuts = random.randint(0, self.subdivs)

                if dd > rr:
                    if l+rr+rr <= xLength:
                        if xEqual:
                            j = j + rr
                            l = l + rr
                        else:
                            i = i + rr*sin(angle)
                            j = j + rr*cos(angle)
                            l = l + rr
                        add_cone(i, j, (i*zSlope)+(zInt-dd/2), rr, dd)
                        if numCuts > 0:
                            bm.edges.ensure_lookup_table()
                            coneEdges = [e for e in bm.edges if e.select == True]
                            verticalEdges = [e for e in coneEdges if e.verts[0].co.z != e.verts[1].co.z]
                            ret = bmesh.ops.subdivide_edges(bm, edges=verticalEdges, cuts=numCuts)
                            #bm.edges.ensure_lookup_table()
                            #bm.verts.ensure_lookup_table()
                            #new_edges = [e for e in ret['geom_split'] if type(e) is bmesh.types.BMEdge]
                            new_verts = [v for v in ret['geom_split'] if type(v) is bmesh.types.BMVert]
                            for t in range(numCuts):
                                v_z = new_verts[0].co.z
                                loop_verts = [v for v in new_verts if v.co.z == v_z]
                                bpy.ops.mesh.select_all(action='DESELECT')
                                for v in loop_verts:
                                    new_verts.pop(new_verts.index(v))
                                    v.select = True
                                obj.data.update()
                                # Set up for random scale
                                rr2 = random.uniform(0.0, 0.7)
                                print("RR2: " + str(rr2))
                                med = get_average(loop_verts)
                                print("Med: " + str(med))
                                # Lerp each vert
                                for v in loop_verts:
                                    v.co = v.co.lerp(med, rr2)
                                bpy.ops.transform.translate(value=(rr * random.random() * pos_neg(), rr * random.random() * pos_neg(), rr * random.random() * pos_neg()))
                            obj.data.update()

                        if xEqual:
                            j = j + rr
                            l = l + rr
                        else:
                            i = i + rr*sin(angle)
                            j = j + rr*cos(angle)
                            l = l + rr
                
                randrad = rad if radM==rad else (rad-radM)*random.random()
                rd = depth if depth==minD else (depth-minD)*random.random()
                
                c = c + 1
                if c >= iterations:
                    print("Too many iterations, please try different values")
                    print("Try increasing gaps between min and max values")
            # Otherwise X and Y values the same, so either verts are on top of each other
            # Or its a vertical line. Either way, we don't like it
            else:
                print("Cannot work on vertical lines")
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