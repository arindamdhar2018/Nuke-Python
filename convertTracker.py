

import nuke
import nukescripts
import nuke.rotopaint as rp
	
# Returns a list with the names of all tracks in the node.
def getTrackerNames(node): 

    n = node["tracks"].toScript()
    rows = n.split("\n")[34:]

    trackers = []

    for i in rows:
        try:            
            trkName = i.split("}")[1].split("{")[0][2:-2]
            if trkName != "":
                trackers.append(trkName)
        except:
            continue

    return trackers
	
	
 # Returns x, y values of a track.
def getTrackerValueAtFrame(node, trackIndex, frame):

    numColumns = 31

    x = node["tracks"].getValueAt(frame, numColumns*trackIndex + 2)
    y = node["tracks"].getValueAt(frame, numColumns*trackIndex + 3)

    return [x, y]
	
	
 # Returns a matrix based on four tracks.
def getMatrixFromTracker(node, trackIndexList, frame, refFrame):

    if node.Class() != "Tracker4" or len(trackIndexList) != 4:
        return False
    
    projectionMatrixTo = nuke.math.Matrix4()
    projectionMatrixFrom = nuke.math.Matrix4()

    toValues = []
    fromValues = []

    numColumns = 31

    for i in range( 0, len(trackIndexList) ):
        for j in range(2):
            toVal = node["tracks"].getValueAt(frame, numColumns*trackIndexList[i] + (2+j))
            fromVal = node["tracks"].getValueAt(refFrame, numColumns*trackIndexList[i] + (2+j))

            toValues.append(toVal)
            fromValues.append(fromVal)

    projectionMatrixTo.mapUnitSquareToQuad(toValues[0], toValues[1], toValues[2], toValues[3], toValues[4], toValues[5], toValues[6], toValues[7])
    projectionMatrixFrom.mapUnitSquareToQuad(fromValues[0], fromValues[1], fromValues[2], fromValues[3], fromValues[4], fromValues[5], fromValues[6], fromValues[7])

    matrix = projectionMatrixTo*projectionMatrixFrom.inverse()    
    matrix.transpose()

    return matrix	

#Nuke panel UI.
class converTo(nukescripts.PythonPanel):

    def __init__(self):

        nukescripts.PythonPanel.__init__(self,"Tracker Node Converter")

        trackerList = getTrackerNames(nuke.selectedNode())

        self.bottom_left = nuke.Enumeration_Knob("bottom_left", "Bottom Left", trackerList)
        self.bottom_right = nuke.Enumeration_Knob("bottom_right", "Bottom Right", trackerList)
        self.upper_right = nuke.Enumeration_Knob("upper_right", "Upper Right", trackerList)
        self.upper_left = nuke.Enumeration_Knob("upper_left", "Upper Left", trackerList)
        self.div1 = nuke.Text_Knob("divider1","" )
        self.first_Frame = nuke.Int_Knob("first_Frame", "first frame")
        self.last_Frame = nuke.Int_Knob("last_Frame", "last frame")
        self.reference_Frame = nuke.Int_Knob("reference_Frame", "reference frame")
        self.set_Frame = nuke.PyScript_Knob('set_Frame', "Set frame")
        self.div2 = nuke.Text_Knob("divider2", "")
        self.node_Name = nuke.Enumeration_Knob("node_Name", "Node", ["CornerPin Match-move", "CornerPin Match-move (Distort)", "CornerPin Stabilize",  "CornerPin Stabilize (Distort)", "RotoPaint"])
        self.div3 = nuke.Text_Knob("divider3", "")
        

        for i in [ self.node_Name, self.div1, self.bottom_left, self.bottom_right, self.upper_right, self.upper_left, self.div2, self.first_Frame, self.last_Frame, self.reference_Frame, self.set_Frame, self.div3]:
            self.addKnob(i)

        # Default values for nuke panel.
        self.bottom_left.setValue(0)
        self.bottom_right.setValue(1)
        self.upper_right.setValue(2)
        self.upper_left.setValue(3)

        self.first_Frame.setValue( int( nuke.root()["first_frame"].value() ) )
        self.last_Frame.setValue( int( nuke.root()["last_frame"].value() ) )
        self.reference_Frame.setValue( int( nuke.root()["frame"].value() ) )
		
    # KnobChange callback.
    def knobChanged(self, knob):
        
        if knob is self.node_Name:
            if self.node_Name.value() == "CornerPin Match-move (Distort)" or self.node_Name.value() == "CornerPin Stabilize (Distort)":
                self.reference_Frame.setEnabled(False)
            else:
                self.reference_Frame.setEnabled(True)

        elif knob is self.set_Frame:
            self.reference_Frame.setValue( int( nuke.root()["frame"].value() ) )


# Main script to run in menu.py
def main_Function():

    try:
        selNode = nuke.selectedNode()

    except ValueError:
        nuke.message("Select a tracker node.")
        return

    if selNode.Class() != "Tracker4":
        nuke.message("Select a tracker node.")
        return

    p = converTo()	
    result = p.showModalDialog()

    if result:

		first_Frame = p.first_Frame.value()
		last_Frame = p.last_Frame.value()
		reference_Frame = p.reference_Frame.value()
		set_Frame = p.set_Frame.value()
		node_Name = p.node_Name.value()
		bottom_leftIndex = int(p.bottom_left.getValue())
		bottom_rightIndex = int(p.bottom_right.getValue())
		upper_rightIndex = int(p.upper_right.getValue())
		upper_leftIndex = int(p.upper_left.getValue())
		trackerListLength = len(getTrackerNames(nuke.selectedNode()))

		#createNode function call.		
		createNode(trackerListLength,bottom_leftIndex,bottom_rightIndex,upper_rightIndex,upper_leftIndex,first_Frame,last_Frame,reference_Frame,set_Frame,node_Name)
		
	
	
# Node create function.
def createNode(trackerListLength,bottom_leftIndex,bottom_rightIndex,upper_rightIndex,upper_leftIndex,first_Frame,last_Frame,reference_Frame,set_Frame,node_Name):

	
	try:
		node = nuke.selectedNode()
		n = node["tracks"]
	except ValueError:
		nuke.message("Select a tracker node.")
		return

	if trackerListLength < 4:
		nuke.message("Please create atleast four tracks in the selected Tracker node.")
		return

	node["selected"].setValue(False)

	
	if node_Name in ["CornerPin Match-move", "CornerPin Match-move (Distort)", "CornerPin Stabilize", "CornerPin Stabilize (Distort)"]:

		create_Node = nuke.createNode("CornerPin2D")

		if node_Name == "CornerPin Match-move" or node_Name == "CornerPin Match-move (Distort)":
			cornerPinMain = "to"
			cornerPinRef = "from"
		else:
			cornerPinMain = "from"
			cornerPinRef = "to"

		main1 = "{0}1".format(cornerPinMain)
		main2 = "{0}2".format(cornerPinMain)
		main3 = "{0}3".format(cornerPinMain)
		main4 = "{0}4".format(cornerPinMain)

		for i in [main1, main2, main3, main4]:
			create_Node[i].setAnimated()

		for i in range(first_Frame, last_Frame+1):
			for j in range(2):
				create_Node[main1].setValueAt(getTrackerValueAtFrame(node, bottom_leftIndex, i)[j], i, j)
				create_Node[main2].setValueAt(getTrackerValueAtFrame(node, bottom_rightIndex, i)[j], i, j)
				create_Node[main3].setValueAt(getTrackerValueAtFrame(node, upper_rightIndex, i)[j], i, j)
				create_Node[main4].setValueAt(getTrackerValueAtFrame(node, upper_leftIndex, i)[j], i, j)

		if node_Name == "CornerPin Match-move" or node_Name == "CornerPin Stabilize":

			# Add reference frame.
			tab = nuke.Tab_Knob("ref", "Reference frame")
			create_Node.addKnob(tab)
			rf = nuke.Int_Knob("rf")
			create_Node.addKnob(rf)
			rf.setLabel("Reference frame")
			create_Node["rf"].setValue(reference_Frame)
			stf = nuke.PyScript_Knob('stf')
			stf.setLabel("Set to this frame")
			create_Node.addKnob(stf)
			stf.setCommand( 'nuke.thisNode()["rf"].setValue(nuke.frame())' )

			create_Node["{0}1".format(cornerPinRef)].setExpression("{0}(rf)".format(main1))
			create_Node["{0}2".format(cornerPinRef)].setExpression("{0}(rf)".format(main2))
			create_Node["{0}3".format(cornerPinRef)].setExpression("{0}(rf)".format(main3))
			create_Node["{0}4".format(cornerPinRef)].setExpression("{0}(rf)".format(main4))

			create_Node["label"].setValue("reference frame: [value rf]")

		# Focus on main tab.
		create_Node["to1"].setFlag(1)

	elif node_Name == "RotoPaint":
	   
		create_Node = nuke.createNode("RotoPaint")         

		curve = create_Node['curves']
		root = curve.rootLayer
		newLayer = rp.Layer(curve)
		name = "tracked layer"
		newLayer.name = name
		root.append(newLayer)
		curve.changed()
		layer = curve.toElement(name)
		transform = layer.getTransform()
		
		for i in range(first_Frame, last_Frame+1):
			matrix = getMatrixFromTracker(node, [bottom_leftIndex,bottom_rightIndex,upper_rightIndex,upper_leftIndex], i, reference_Frame)
			for j in range(16):
				extraMatrixKnob = transform.getExtraMatrixAnimCurve(0,j)
				extraMatrixKnob.addKey(i,matrix[j])

		create_Node["label"].setValue("reference frame: {0}".format(reference_Frame))


		# Setup node.
		create_Node["xpos"].setValue(node["xpos"].value())
		create_Node["ypos"].setValue(node["ypos"].value()+50)
		create_Node["selected"].setValue(False)
		create_Node.setInput(0, None)	
