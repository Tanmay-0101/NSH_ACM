satellites={}
debris={}

def update_objects(objects):
    processed=0
    for obj in objects:
        state={
            "position": [obj.r.x, obj.r.y, obj.r.z],
            "velocity": [obj.v.x, obj.v.y, obj.v.z]
        }

        if(obj.type=="SATELLITE"):
            satellites[obj.id]=state
        else:
            debris[obj.id]=state

        processed+=1

    return processed