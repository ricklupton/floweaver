v2.1.0 (unreleased)
===================

- Bundles to/from Elsewhere with `flow_selection` set are now handled properly. For example, if there are two flows with two different materials "m1" and "m2", leaving a process group, there can be a bundle defined as `Bundle("source", Elsewhere, flow_selection="material == 'm1'", waypoints=["m1_waypoint"])` which will correctly include only the "m1" flow. The change is that the "m2" flow will now also be shown as a generic "to elsewhere" flow, whereas previously it was ignored. This ensures processes balance even when not all inputs/outputs are explicitly included.

v2.0.0
======
- TODO document changes!

v1.1.7
======
- generalise handling of multiple samples in dataset
