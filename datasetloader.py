from torchvision.datasets import VisionDataset

from PIL import Image

import os
import os.path
import sys
import gc

import pandas as pd
import numpy as np
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
import gc

from google.colab import drive


def pil_loader(path):
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    with open(path, 'rb') as f:
        img = Image.open(f)
        return img.convert('RGB')


class ROD(VisionDataset):

    def __init__(self, root, split='train', transform=None, target_transform=None, blacklisted_classes=[]):
        super(ROD, self).__init__(root, transform=transform, target_transform=target_transform)

        self.split = split # This defines the split you are going to use
                           # (split files are called 'train.txt' and 'test.txt')
            
        #self.blacklist_classes = blacklisted_classes  # Needed just is using custom mapper
        '''
        - Here you should implement the logic for reading the splits files and accessing elements
        - If the RAM size allows it, it is faster to store all data in memory
        - PyTorch Dataset classes use indexes to read elements
        - You should provide a way for the __getitem__ method to access the image-label pair
          through the index
        - Labels should start from 0, so for Caltech you will have lables 0...100 (excluding the background class) 
        '''
        
        split_path = os.path.join(root, split+".txt")  # 
        split_file = np.loadtxt(split_path, dtype='str')
        

        imgs_and_labels = []
        for line in split_file:
          image_path, classN = line
          class_label = image_path.split('/')[1]
          if class_label in blacklisted_classes:
            continue
          
          rgb_img_path = root+image_path.replace("???", "rgb").replace("***","crop")
          depth_img_path = root+image_path.replace("???", "rgb").replace("***","depthcrop")
          rgb_img = pil_loader(rgb_img_path)
          depth_img = pil_loader(rgb_img_path)
          imgs_and_labels.append([rgb_img, depth_img, class_label])
          

        self.data = pd.DataFrame(imgs_and_labels, columns=['rgb', 'depth', 'class'])
        del(imgs_and_labels)
        gc.collect()
        # USing custom enc, notthe txt given one
        le = preprocessing.LabelEncoder()
        self.le = le
        self.data['encoded_class'] = le.fit_transform(self.data['class'])        

    def __getitem__(self, index):
        '''
        __getitem__ should access an element through its index
        Args:
            index (int): Index
        Returns:
            tuple: (sample, depth_image, target) where target is class_index of the target class.
        '''

        rgb_image, depth_image, label = self.data.iloc[index]['rgb'], self.data.iloc[index]['depth'], self.data.iloc[index]['encoded_class'] # Provide a way to access image and label via index
                           # Image should be a PIL Image
                           # label can be int
        
        # Applies preprocessing when accessing the image
        if self.transform is not None:
            image = self.transform(image)
         
        if self.transform is not None:
            depth_image = self.transform(depth_image)
            
        return image, depth_image, label

    def __len__(self):
        '''
        The __len__ method returns the length of the dataset
        It is mandatory, as this is used by several other components
        '''
        length = len(self.data) # Provide a way to get the length (number of elements) of the dataset
        return length
    
    def split_data(self, val_size=0.5):
        """
        Split the train set in to train and validation set (stratified sampling)
        
        args:
            val_size: If float, should be between 0.0 and 1.0 and represent the proportion of the dataset to include for validation
        returns:
            (train_indexes[], val_indexes[]): lists of indexes for train and validation split.
        """

        X_train, X_val = train_test_split(self.data, test_size=val_size, stratify=self.data['encoded_class'] )
    
        # Get (not contiguous) indexes for a stratified split 
        train_indexes, val_indexes = X_train.index.values, X_val.index.values

        # Create an ordered dataframe to have contiguous index ranges (ie. 0-2000, 2000-4000)
        new_train_dataset = self.data.filter(train_indexes, axis=0)
        new_val_dataset = self.data.filter(val_indexes, axis=0)
        new_dataset = pd.DataFrame(new_train_dataset).reset_index(drop=True)
        new_dataset = new_dataset.append(new_val_dataset, ignore_index=True)
        # Assign new dataframe to data attribute
        self.data = new_dataset
        # Define the contiguous indexes by using just length
        train_indexes, val_indexes = list(range(len(train_indexes))), list(range(len(train_indexes), len(train_indexes)+len(X_val.index.values)))

        return train_indexes, val_indexes
    
    def reduce_data(self, tokeep=0.6):
        """
        Reduce the entire set using a stratified sampling
        
        args:
            tokeep: If float, should be between 0.0 and 1.0 and represent the proportion of the dataset to include
        returns:
            (Int, int): Indexes of remaining elements (contigous), Num of deleted elements.
        """

        X_train, X_val = train_test_split(self.data, test_size=tokeep, stratify=self.data['encoded_class'] )
    
        # Get (not contiguous) indexes for a stratified split 
        del_indexes, new_indexes = X_train.index.values, X_val.index.values

        # Create an ordered dataframe to have contiguous index ranges (ie. 0-2000)
        new_val_dataset = self.data.filter(new_indexes, axis=0)
        new_dataset = pd.DataFrame(new_val_dataset).reset_index(drop=True)
        # Assign new dataframe to the cutted new dataset
        self.data = new_dataset

        gc.collect()  # Force garbace collector 
        # Define the contiguous indexes by using just length
        new_indexes, del_indexes = list(range(len(new_indexes))), list(range(len(del_indexes), len(new_indexes)+len(del_indexes)))
        return new_indexes, len(del_indexes)
    
    def get_classes(self):
        """Return the classes as list """
        
        return self.le.classes_#self.data['class']
    
    def get_encoded_classes(self):
        """Return the ecoded classes mapping dict"""
        
        class_mapping = {self.le.transform(v):v for v in self.le.classes_}
        return class_mapping

class SynROD(VisionDataset):

    def __init__(self, root, transform=None, target_transform=None, blacklisted_classes=[], verbose=0):
        super(SynROD, self).__init__(root, transform=transform, target_transform=target_transform)

            
        #self.blacklist_classes = blacklisted_classes  # Needed just is using custom mapper
        '''
        - Here you should implement the logic for reading the splits files and accessing elements
        - If the RAM size allows it, it is faster to store all data in memory
        - PyTorch Dataset classes use indexes to read elements
        - You should provide a way for the __getitem__ method to access the image-label pair
          through the index
        - Labels should start from 0, so for Caltech you will have lables 0...100 (excluding the background class) 
        '''
        
        imgs_and_labels = []
        missing_couple = 0
        parent, dirs, files = next(os.walk(root))
        for dir_name in dirs:  # Iterate over class-named folder (apple, ball, banana)
          class_label = dir_name
          depth_folder_path  = os.path.join(root, dir_name, "depth") 
          rgb_folder_path  = os.path.join(root, dir_name, "rgb") 
          
          _, _, imgs = next(os.walk(rgb_folder_path))
          for img in imgs:
            rgb_img_path  = os.path.join(rgb_folder_path, img) 
            rgb_img = pil_loader(rgb_img_path)
            depth_img_path  = os.path.join(depth_folder_path, img) 
            if not os.path.isfile(depth_img_path):
              missing_couple += 1
              if verbose > 0:
                print("[INFO] Skipping 1 sample because of missing depth partner")
                print(depth_img_path, "doesnt exist")
              continue
              # raise Exception("For each rgb image you NEED the depth version too")
            depth_img = pil_loader(depth_img_path)
            imgs_and_labels.append([rgb_img, depth_img, class_label])
          
        print("[INFO] A total of ", missing_couple, "samples were skipped because it's missing of their depth map")
        self.data = pd.DataFrame(imgs_and_labels, columns=['rgb', 'depth', 'class'])
        
        # USing custom enc, notthe txt given one
        le = preprocessing.LabelEncoder()
        self.le = le
        self.data['encoded_class'] = le.fit_transform(self.data['class'])        

    def __getitem__(self, index):
        '''
        __getitem__ should access an element through its index
        Args:
            index (int): Index
        Returns:
            tuple: (sample,depth_image, target) where target is class_index of the target class.
        '''

        rgb_image, depth_image, label = self.data.iloc[index]['rgb'], self.data.iloc[index]['depth'], self.data.iloc[index]['encoded_class'] # Provide a way to access image and label via index
                           # Image should be a PIL Image
                           # label can be int

        # Applies preprocessing when accessing the image
        if self.transform is not None:
            image = self.transform(image)
        
        if self.transform is not None:
            depth_image = self.transform(depth_image)
            
        return image, depth_image, label

    def __len__(self):
        '''
        The __len__ method returns the length of the dataset
        It is mandatory, as this is used by several other components
        '''
        length = len(self.data) # Provide a way to get the length (number of elements) of the dataset
        return length
    
    def split_data(self, val_size=0.5):
        """
        Split the train set in to train and validation set (stratified sampling)
        
        args:
            val_size: If float, should be between 0.0 and 1.0 and represent the proportion of the dataset to include for validation
        returns:
            (train_indexes[], val_indexes[]): lists of indexes for train and validation split.
        """

        X_train, X_val = train_test_split(self.data, test_size=val_size, stratify=self.data['encoded_class'] )
    
        # Get (not contiguous) indexes for a stratified split 
        train_indexes, val_indexes = X_train.index.values, X_val.index.values

        # Create an ordered dataframe to have contiguous index ranges (ie. 0-2000, 2000-4000)
        new_train_dataset = self.data.filter(train_indexes, axis=0)
        new_val_dataset = self.data.filter(val_indexes, axis=0)
        new_dataset = pd.DataFrame(new_train_dataset).reset_index(drop=True)
        new_dataset = new_dataset.append(new_val_dataset, ignore_index=True)
        # Assign new dataframe to data attribute
        self.data = new_dataset
        # Define the contiguous indexes by using just length
        train_indexes, val_indexes = list(range(len(train_indexes))), list(range(len(train_indexes), len(train_indexes)+len(X_val.index.values)))

        return train_indexes, val_indexes

    def reduce_data(self, tokeep=0.6):
        """
        Reduce the entire set using a stratified sampling
        
        args:
            tokeep: If float, should be between 0.0 and 1.0 and represent the proportion of the dataset to include
        returns:
            (Int, int): Indexes of remaining elements (contigous), Num of deleted elements.
        """

        X_train, X_val = train_test_split(self.data, test_size=tokeep, stratify=self.data['encoded_class'] )
    
        # Get (not contiguous) indexes for a stratified split 
        del_indexes, new_indexes = X_train.index.values, X_val.index.values

        # Create an ordered dataframe to have contiguous index ranges (ie. 0-2000)
        new_val_dataset = self.data.filter(new_indexes, axis=0)
        new_dataset = pd.DataFrame(new_val_dataset).reset_index(drop=True)
        # Assign new dataframe to the cutted new dataset
        self.data = new_dataset

        gc.collect()  # Force garbace collector 
        # Define the contiguous indexes by using just length
        new_indexes, del_indexes = list(range(len(new_indexes))), list(range(len(del_indexes), len(new_indexes)+len(del_indexes)))
        return new_indexes, len(del_indexes)
    
    def get_classes(self):
        """Return the classes as list """
        
        return self.le.classes_#self.data['class']
    
    def get_encoded_classes(self):
        """Return the ecoded classes mapping dict"""
        
        class_mapping = {self.le.transform(v):v for v in self.le.classes_}
        return class_mapping
