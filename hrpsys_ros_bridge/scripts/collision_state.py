#!/usr/bin/env python
import roslib; roslib.load_manifest("hrpsys_ros_bridge")

import OpenRTM_aist.RTM_IDL # for catkin

import rospy
from diagnostic_msgs.msg import *

import os
import hrpsys
import rtm

from rtm import *
from OpenHRP import *

import socket
import time
import numpy

from std_msgs.msg import ColorRGBA
from geometry_msgs.msg import Point
from geometry_msgs.msg import Vector3
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

def rtc_init () :
    global ms, co, co_svc, root_link_name

    initCORBA()
    ms = rtm.findRTCmanager(rtm.nshost)
    while ms == None :
        time.sleep(1);
        ms = rtm.findRTCmanager(rtm.nshost)
        rospy.loginfo("[collision_state.py] wait for RTCmanager : ",ms)

    co = rtm.findRTC("co")
    if co == None:
        rospy.logerr("Could not found CollisionDetector, exiting...")
        exit(1)
    co_svc = narrow(co.service("service0"), "CollisionDetectorService")

    if modelfile:
        #import CosNaming
        obj = rtm.rootnc.resolve([CosNaming.NameComponent('ModelLoader', '')])
        mdlldr = obj._narrow(ModelLoader_idl._0_OpenHRP__POA.ModelLoader)
        rospy.loginfo("  bodyinfo URL = file://",modelfile)
        body_info = mdlldr.getBodyInfo("file://"+modelfile)
        root_link_name = body_info._get_links()[0].name
    else:
        root_link_name = "WAIST"



def collision_state() :
    global ms, co_svc, root_link_name

    diagnostic = DiagnosticArray()
    diagnostic.header.stamp = rospy.Time.now()

    collision_status = co_svc.getCollisionStatus()

    # check if ther are collision
    status = DiagnosticStatus(name = 'CollisionDetector', level = DiagnosticStatus.OK, message = "Ok")

    #if any(a): # this calls omniORB.any
    for collide in collision_status[1].collide:
        if collide:
            status.level   = DiagnosticStatus.ERROR
            status.message = "Robots is in collision mode"

    status.values.append(KeyValue(key = "Time", value = str(collision_status[1].time)))
    status.values.append(KeyValue(key = "Computation Time", value = str(collision_status[1].computation_time)))
    status.values.append(KeyValue(key = "Safe Posture", value = str(collision_status[1].safe_posture)))
    status.values.append(KeyValue(key = "Recover Time", value = str(collision_status[1].recover_time)))
    status.values.append(KeyValue(key = "Loop for check", value = str(collision_status[1].loop_for_check)))

    frame_id = root_link_name # root id
    markerArray = MarkerArray()
    for line in collision_status[1].lines:
        p1 = Point(line[0][0],line[0][1],line[0][2])
        p2 = Point(line[1][0],line[1][1],line[1][2])

        sphere_color = ColorRGBA(0,1,0,1)
        line_length = numpy.linalg.norm(numpy.array((p1.x,p1.y,p1.z))-numpy.array((p2.x,p2.y,p2.z)))
        if (line_length < 0.1) :
           sphere_color = ColorRGBA(line_length*10,1-line_length*10,0,1)

        marker = Marker()
        marker.header.frame_id = frame_id
        marker.type = marker.LINE_LIST
        marker.action = marker.ADD
        marker.color = sphere_color
        marker.points = [p1, p2]
        marker.scale.x = 0.01
        markerArray.markers.append(marker)

        sphere_scale = Vector3(0.02, 0.02, 0.02)
        marker = Marker()
        marker.header.frame_id = frame_id
        marker.type = marker.SPHERE
        marker.action = marker.ADD
        marker.scale = sphere_scale
        marker.color = sphere_color
        marker.pose.orientation.w = 1.0
        marker.pose.position = p1
        markerArray.markers.append(marker)

        marker = Marker()
        marker.header.frame_id = frame_id
        marker.type = marker.SPHERE
        marker.action = marker.ADD
        marker.scale = sphere_scale
        marker.color = sphere_color
        marker.pose.orientation.w = 1.0
        marker.pose.position = p2
        markerArray.markers.append(marker)


    id = 0
    for m in markerArray.markers:
        m.id = id
        id += 1

    pub_collision.publish(markerArray)
    diagnostic.status.append(status)
    pub_diagnostics.publish(diagnostic)


modelfile = None
if __name__ == '__main__':
    if len(sys.argv) > 1 :
        modelfile = sys.argv[1]

    try:
        rtc_init()

        rospy.init_node('collision_state_diagnostics')
        pub_diagnostics = rospy.Publisher('diagnostics', DiagnosticArray)
        pub_collision = rospy.Publisher('collision_detector_marker_array', MarkerArray)

        r = rospy.Rate(50)

        while not rospy.is_shutdown():
            try :
                collision_state()
            except (omniORB.CORBA.TRANSIENT, omniORB.CORBA.BAD_PARAM, omniORB.CORBA.COMM_FAILURE, omniORB.CORBA.OBJECT_NOT_EXISTS), e :
                print "[collision_state.py] catch exception, restart rtc_init", e
                rtc_init(hostname)
            except Exception as e:
                print "[collision_state.py] catch exception", e
            r.sleep()

    except rospy.ROSInterruptException: pass




