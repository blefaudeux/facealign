import cv, math

def getRotMatrix():
	rad = math.radians(30)
	alpha = math.cos(rad)
	beta = math.sin(rad)
	
	m = [[alpha, beta, (1 - alpha)*-1600 - beta*-1600], 
	     [-beta, alpha, beta*-1600 - (1 - alpha)*-1600]]

#	m = [[alpha, beta, 0], 
#	     [-beta, alpha, 0]]

	
	return m
	
def getTransMatrix():
	m = [[1, 0, 2816/2 + 400], [0, 1, 2112/2 - 400]]
	return m
	
def mergeMat(m, cvMat):
	cv.mSet(transl, 0, 0, m[0][0])
	cv.mSet(transl, 1, 1, m[1][1])
	cv.mSet(transl, 0, 1, m[0][1])
	cv.mSet(transl, 0, 2, m[0][2])
	cv.mSet(transl, 1, 2, m[1][2])
	cv.mSet(transl, 1, 0, m[1][0])
	
def markPoint(img, pt, color=(0,0,255), width=20):
	polys = [[(pt[0]-width/2, pt[1]-width/2), (pt[0]+width/2, pt[1]-width/2), (pt[0]+width/2, pt[1]+width/2), (pt[0]-width/2, pt[1]+width/2)]]
	cv.FillPoly(img, polys, color)

img = cv.LoadImage('../dat/raw/DSC05172.JPG', 1)
markPoint(img, (2816/2+100, 2112/2+100))
#newImg = cv.CreateImage((2816,2112), cv.IPL_DEPTH_8U, 3)
newImg = cv.CloneImage(img)
transl = cv.CreateMat(2, 3, cv.CV_32FC1)

m = getRotMatrix()
mergeMat(m, transl)
cv.GetQuadrangleSubPix(img, newImg, transl)

cv.SaveImage('ass600.jpg', newImg)
