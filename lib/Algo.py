# 
import cv2
import numpy as np
import imutils
import rpyc

class Algo:

  def __init__(self, name, settings):
    self.settings = settings
    self.log = settings.log
    if self.settings.use_ml == 'remote':
      self.proxy = rpyc.connect(settings.ml_server_ip, settings.ml_port, 
          config={'allow_public_attrs': True})
    else:
      if name == 'Cnn_Shapes':
        self.classes = ["background", "aeroplane", "bicycle", "bird", "boat",
          "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
          "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
          "sofa", "train", "tvmonitor"]
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
        self.dlnet = cv2.dnn.readNetFromCaffe("shapes/MobileNetSSD_deploy.prototxt.txt",
          "shapes/MobileNetSSD_deploy.caffemodel")
      elif name == 'Cnn_Face':
        self.dlnet = cv2.dnn.readNetFromCaffe("face/deploy.prototxt.txt", 
            "face/res10_300x300_ssd_iter_140000.caffemodel")
      elif name.startswith('Haar'):
        list = name.split('_')
        haar = 'haar/fullbody_recognition_model.xml'
        if list[1] == 'Face':
          haar = 'haar/facial_recognition_model.xml'
        elif list[1] == 'FullBody':
          haar = 'haar/fullbody_recognition_model.xml'
        elif list[1] == 'UpperBody':
          haar = 'haar/upperbody_recognition_model.xml'
        self.object_classifier = cv2.CascadeClassifier(haar)
      elif name == 'Hog_People':
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

      self.proxy = self.detectors
      
  # local detectors below - remote detecters call in differently
  def detectors(self, name, debug, threshold, image):
    if name == 'Cnn_Face':
      result, n = self.face_detect(image, threshold, debug)
    elif name == 'Cnn_Shapes':
      result, n = self.shapes_detect(image, threshold, debug)
    elif name.startswith('Haar'):
      result, n = self.haar_detect(image, threshold, debug)
    elif name == 'Hog_People':
      result, n = self.hog_detect(image, threshold, debug)
    return (result, n)
    
  def face_detect(self, image, threshold, debug):
    n = 0
    (h, w) = image.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
      (300, 300), (104.0, 177.0, 123.0))
    # pass the blob through the network and obtain the detections and
    # predictions
    self.dlnet.setInput(blob)
    detections = self.dlnet.forward()
    n = 0
    for i in range(0, detections.shape[2]):
      confidence = detections[0, 0, i, 2]
      if confidence > 0.5:
        n = n + 1
        
    #self.log('Faces: %d' % n);
    return (n > 0, n)

  def shapes_detect(self, image, threshold, debug):
    #self.log("shape check")
    n = 0
    # grab the frame from the threaded video stream and resize it
    # to have a maximum width of 400 pixels
    frame = imutils.resize(image, width=400)
  
    # grab the frame dimensions and convert it to a blob
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
      0.007843, (300, 300), 127.5)
  
    # pass the blob through the network and obtain the detections and
    # predictions
    self.dlnet.setInput(blob)
    detections = self.dlnet.forward()
  
    # loop over the detections
    for i in np.arange(0, detections.shape[2]):
      # extract the confidence (i.e., probability) associated with
      # the prediction
      confidence = detections[0, 0, i, 2]
  
      # filter out weak detections by ensuring the `confidence` is
      # greater than the minimum confidence
      if confidence > threshold:
        # extract the index of the class label from the
        # `detections`, then compute the (x, y)-coordinates of
        # the bounding box for the object
        idx = int(detections[0, 0, i, 1])
        if idx == 15:
          n += 1
          break
        if debug:
          box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
          (startX, startY, endX, endY) = box.astype("int")
    
          # draw the prediction on the frame
          label = "{}: {:.2f}%".format(self.classes[idx],
            confidence * 100)
          cv2.rectangle(frame, (startX, startY), (endX, endY),
            COLORS[idx], 2)
          y = startY - 15 if startY - 15 > 15 else startY + 15
          cv2.putText(frame, label, (startX, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors[idx], 2)
  
    # show the output frame
    if debug:
      cv2.imshow("Detect", frame)
    self.log.info("shapes = %d" % n)
    return (n > 0, n)

  # ----- haar detectors
  def haar_detect(self, frame, threshold, debug):
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    objects = self.object_classifier.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    #self.log("haar detect: %d" % len(objects))
    return (len(objects) > 0, len(objects))
    
  # ------ Hog detectors 
  def hog_detect(self, frame, threshold, debug):
    # resizing for faster detection
    #frame = cv2.resize(frame, (640, 480))
    # using a greyscale picture, also for faster detection
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    # detect people in the image
    # returns the bounding boxes for the detected objects
    boxes, weights = self.hog.detectMultiScale(frame, winStride=(8,8) )

    boxes = np.array([[x, y, x + w, y + h] for (x, y, w, h) in boxes])
    n = len(boxes)
    if n > 0:
      for (xA, yA, xB, yB) in boxes:
          # display the detected boxes in the colour picture
          cv2.rectangle(frame, (xA, yA), (xB, yB),
                            (0, 255, 0), 2)
          print("Detected", xA, yA, xB, yB)
      if debug:
        cv2.imshow('frame',frame)
    return (n > 0), n
 
