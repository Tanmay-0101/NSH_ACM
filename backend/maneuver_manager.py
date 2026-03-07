scheduled_maneuvers = [] #to become a priority queue based on burn time


def schedule_maneuver(maneuver_request):

    scheduled_maneuvers.append(maneuver_request)

    return True