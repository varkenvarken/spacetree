spacetree
=========

A Blender add-on to create tree objects with the space colonization algorithm

Currently part of Blender contrib:

https://svn.blender.org/svnroot/bf-extensions/contrib/py/scripts/addons/add_mesh_space_tree/

Documentation (work in progress):

http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Add_Mesh/Add_Space_Tree

INSTALLATION
============

If you have installed Blender from a daily build, this add-on is already bundled. If you wnt to try a newer version you have to make sure that the distributed version is removed first:

- quit Blender
- go to the installation directory of the contributed addons, e.g. <BlenderInstallDir>\2.69\scripts\addons_contrib
- remove the add_mesh_space_tree directory
- download add_mesh_space_tree.zip from the release directory (do not use the download as .zip for the complete repository, that won't work: the .zip in the release dir is a package Blender cn use directly)
- open Blender
- choose File->User preferences->Addons->Install from file and select the downloaded .zip, click install
- don't forget to check the enable addon checkbox once it it is installed

If you want to enable it later it live in the Add Mesh section of the addons and is called 'SCA Tree generator'.

To use the addon (in the 3DVIEW) click Add->Mesh->Add tree to scene, the options are in the toolbar panel (Ctrl-T)

NOTE: the tree is generated at the position of the 3d cursor. If you don't see the tree, check that you can see the cursor.

NOTE: generatin a tree can take quite some time, therefore the tree does NOT change immediately if you tweak an option. You have to click the 'update tree' button to generate a new tree after you changed the settings. 



