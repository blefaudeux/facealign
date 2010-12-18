import cv, sys, os

def main():
	# Get input files, sort
	inputDir = sys.argv[1]
	files = os.listdir(inputDir)
	files.sort()
	
	i=0
	# For every JPG in the given directory
	for file in files:
		# If a jpeg file
		if file.upper().endswith('.JPG') or file.upper().endswith('.JPEG'):
			filePath = os.path.join(inputDir, file)
			print('Processing ' + filePath)
			
			# Open the image, cropToEyes sets ROI wrt eyes
			image = cv.LoadImage(filePath, 1); # Second argument is for 0:grayscale, 1:color
			cascade = cv.Load('/usr/local/share/opencv/haarcascades/haarcascade_frontalface_default.xml')
			faces = cv.HaarDetectObjects(image, cascade, cv.CreateMemStorage())

			for (x,y,w,h),n in faces:
				cv.Rectangle(image, (x, y), (x+w, y+h), (255,255,255))

			
			# Save in the format inputDir/out/<originalName>.<originalExtension>
			#cv.SaveImage(inputDir+'/out/'+str(i)+'.jpg', image)
			cv.SaveImage('/home/rob/facealign/dat/raw/out/'+str(i)+'.jpg', image)
			print('saved to: ' + '/home/rob/facealign/dat/raw/out/'+str(i)+'.jpg')
			
			i = i+1
			
if __name__ == "__main__":
	main()