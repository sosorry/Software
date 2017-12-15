#!/usr/bin/env python
import numpy as np
import cv2


class Edge(object):
    '''class for representing edges'''

    def __init__(self, ptA, ptB):
        # start and end point of line
        self.ptA = ptA
        self.ptB = ptB

        # auxiliary variables
        self.length = np.linalg.norm(ptB - ptA)
        self.n_par = (ptB - ptA) / self.length
        self.n_perp = np.array([self.n_par[1], -self.n_par[0]])


class EdgeModel(object):
    '''class for representing an object composed of edges'''

    def __init__(self, object_type, pixels_per_meter, ctrl_pts_density):
        # edge model parameters
        self.tile_width = 0.5842 # in meters (23in)
        self.tile_overlap = 0.0254
        self.white_tape_width = 0.0508
        self.red_tape_width = 0.0508
        self.yellow_tape_width = 0.0254
        self.lane_length = 0.1254
        self.ppm = 1

        # generate edges
        if object_type == 'FOUR_WAY_INTERSECTION':
            self.edges, self.num_edges = self.GenerateIntersection(4, pixels_per_meter)

        elif object_type == 'THREE_WAY_INTERSECTION':
            self.edges, self.num_edges = self.GenerateIntersection(3, pixels_per_meter)

        else:
            # TODO THROW ERROR
            return

        # generate control points
        self.ctrl_pts, self.ctrl_pts_homogeneous, self.ctrl_pts_n_perp, self.num_ctrl_pts = self.GenerateControlPoints(
            ctrl_pts_density)

    def GenerateControlPoints(self, ctrl_pts_density):
        # computer number of control points
        ctrl_pts_per_edge = np.zeros(shape=(self.num_edges), dtype=int)
        for i in range(0, self.num_edges):
            ctrl_pts_per_edge[i] = np.floor(self.edges[i].length * ctrl_pts_density) + 1

        num_ctrl_pts = np.sum(ctrl_pts_per_edge, axis=0, dtype=int)

        # generate control points
        ctrl_pts = np.zeros(shape=(2, num_ctrl_pts), dtype=float)
        ctrl_pts_homogeneous = np.zeros(shape=(3, num_ctrl_pts), dtype=float)
        ctrl_pts_n_perp = np.zeros(shape=(2, num_ctrl_pts), dtype=float)
        k = 0
        for i in range(0, self.num_edges):
            offset = (self.edges[i].length - (ctrl_pts_per_edge[i] - 1.0) / ctrl_pts_density) / 2.0

            for j in range(0, ctrl_pts_per_edge[i]):
                ctrl_pts[:, k] = self.edges[i].ptA + (offset + np.float(j) / ctrl_pts_density) * self.edges[
                    i].n_par
                ctrl_pts_n_perp[:, k] = self.edges[i].n_perp
                k += 1

        ctrl_pts_homogeneous[0:2, :] = ctrl_pts[:, :]
        ctrl_pts_homogeneous[2, :] = 1

        return ctrl_pts, ctrl_pts_homogeneous, ctrl_pts_n_perp, num_ctrl_pts

    def ComputeControlPointsLocation(self, x, y, theta):
        # generate motion matrix
        R = np.array([[np.cos(theta), np.sin(theta)], [-np.sin(theta), np.cos(theta)]])
        t = np.dot(R, np.array([x, y])*self.ppm)
        M = np.array([[np.cos(theta), np.sin(theta), -t[0]], [-np.sin(theta), np.cos(theta), -t[1]], [0.0, 0.0, 1.0]])

        return np.dot(M, self.ctrl_pts_homogeneous), np.dot(R, self.ctrl_pts_n_perp)


    def GenerateIntersection(self, num_exits, pixels_per_meter):
        if not (num_exits == 3 or num_exits == 4):
            # TODO throw error
            return

        # update pixels per meter to compute correct control point locations
        self.ppm = pixels_per_meter

        # create auxiliary points
        pt1 = np.array([-self.lane_length, 0.5 * (self.tile_width - self.tile_overlap) + 0.5 * self.yellow_tape_width],
                       dtype=float)
        pt2 = np.array(
            [self.white_tape_width, 0.5 * (self.tile_width - self.tile_overlap) + 0.5 * self.yellow_tape_width],
            dtype=float)

        pt3 = np.array([-self.lane_length, 0.5 * (self.tile_width - self.tile_overlap) - 0.5 * self.yellow_tape_width],
                       dtype=float)
        pt4 = np.array([0.0, 0.5 * (self.tile_width - self.tile_overlap) - 0.5 * self.yellow_tape_width], dtype=float)
        pt5 = np.array(
            [self.white_tape_width, 0.5 * (self.tile_width - self.tile_overlap) - 0.5 * self.yellow_tape_width],
            dtype=float)

        pt6 = np.array([-self.lane_length, self.white_tape_width], dtype=float)
        pt7 = np.array([0.0, self.white_tape_width], dtype=float)
        pt8 = np.array([self.white_tape_width, self.white_tape_width], dtype=float)

        pt9 = np.array([-self.lane_length, 0.0], dtype=float)
        pt10 = np.array([0.0, 0.0], dtype=float)

        pt11 = np.array([0.0, -self.lane_length])
        pt12 = np.array([self.white_tape_width, -self.lane_length])

        pt13 = np.array([self.tile_width - self.tile_overlap + self.lane_length, self.white_tape_width], dtype=float)
        pt14 = np.array([self.tile_width - self.tile_overlap + self.lane_length, 0.0], dtype=float)

        # convert positions of auxiliary points from meter to pixels
        pt1 = pt1 * pixels_per_meter
        pt2 = pt2 * pixels_per_meter
        pt3 = pt3 * pixels_per_meter
        pt4 = pt4 * pixels_per_meter
        pt5 = pt5 * pixels_per_meter
        pt6 = pt6 * pixels_per_meter
        pt7 = pt7 * pixels_per_meter
        pt8 = pt8 * pixels_per_meter
        pt9 = pt9 * pixels_per_meter
        pt10 = pt10 * pixels_per_meter
        pt11 = pt11 * pixels_per_meter
        pt12 = pt12 * pixels_per_meter
        pt13 = pt13 * pixels_per_meter
        pt14 = pt14 * pixels_per_meter

        # create template for regular intersection exit
        edges_regular = []
        edges_regular.append(Edge(pt1, pt2))
        edges_regular.append(Edge(pt3, pt5))
        edges_regular.append(Edge(pt6, pt8))
        edges_regular.append(Edge(pt9, pt10))
        edges_regular.append(Edge(pt4, pt7))
        edges_regular.append(Edge(pt10, pt11))
        edges_regular.append(Edge(pt2, pt12))

        # create template for three way intersection exit
        edges_special = []
        edges_special.append(Edge(pt1, pt2))
        edges_special.append(Edge(pt3, pt5))
        edges_special.append(Edge(pt6, pt13))
        edges_special.append(Edge(pt9, pt14))
        edges_special.append(Edge(pt4, pt7))
        edges_special.append(Edge(pt2, pt8))

        # generate intersection model
        edges = []
        if num_exits == 4:
            for k in range(0, 4):
                # compute translation
                if k == 0:
                    t = np.array([0.0, 0.0], dtype=float) * pixels_per_meter
                elif k == 1:
                    t = np.array([self.tile_width - self.tile_overlap, 0.0], dtype=float) * pixels_per_meter
                elif k == 2:
                    t = np.array([self.tile_width - self.tile_overlap, self.tile_width - self.tile_overlap],
                                 dtype=float) * pixels_per_meter
                else:
                    t = np.array([0.0, self.tile_width - self.tile_overlap]) * pixels_per_meter

                # compute rotation
                theta = k * 0.5 * np.pi
                R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]], dtype=float)

                # translate and rotate template
                for l in range(0, len(edges_regular)):
                    ptA_rot = np.dot(R, edges_regular[l].ptA) + t
                    ptB_rot = np.dot(R, edges_regular[l].ptB) + t
                    edges.append(Edge(ptA_rot, ptB_rot))

        elif num_exits == 3:
            for k in range(0, 3):
                # compute translation
                if k == 0:
                    t = np.array([0.0, 0.0], dtype=float) * pixels_per_meter
                elif k == 1:
                    t = np.array([self.tile_width - self.tile_overlap, 0.0], dtype=float) * pixels_per_meter
                elif k == 2:
                    t = np.array([self.tile_width - self.tile_overlap, self.tile_width - self.tile_overlap],
                                 dtype=float) * pixels_per_meter
                else:
                    t = np.array([0.0, self.tile_width - self.tile_overlap]) * pixels_per_meter

                # compute rotation
                theta = k * 0.5 * np.pi
                R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]], dtype=float)

                # translate and rotate template
                if k < 2:
                    for l in range(0, len(edges_regular)):
                        ptA_rot = np.dot(R, edges_regular[l].ptA) + t
                        ptB_rot = np.dot(R, edges_regular[l].ptB) + t
                        edges.append(Edge(ptA_rot, ptB_rot))
                else:
                    for l in range(0, len(edges_special)):
                        ptA_rot = np.dot(R, edges_special[l].ptA) + t
                        ptB_rot = np.dot(R, edges_special[l].ptB) + t
                        edges.append(Edge(ptA_rot, ptB_rot))

        return edges, len(edges)
