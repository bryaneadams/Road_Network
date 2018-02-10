import os
import time
import numpy as np
import pandas as pd
from skimage.io import imread
import torch.utils.data as data

import warnings
warnings.filterwarnings('ignore')

# relative dataset storage path for test dataset
prefix = '../data'
# relative dataset storage path for train dataset
prefix_train = '../'
# metadata and mask_df files
meta_prefix = '../'
meta_data_file = os.path.join(meta_prefix,'metadata.csv')
mask_df_file = os.path.join(meta_prefix,'mask_df.csv')
wide_mask_df_file = 'new_masks.csv'
layered_mask_df_file = 'new_masks_layered.csv'

# high level function that return list of images and cities under presets
def get_test_dataset(preset,
                     preset_dict,
                     city='all',
                     path_prefix=''):
    meta_df = pd.read_csv(meta_data_file)
    
    test_folders = ['AOI_2_Vegas_Roads_Test_Public','AOI_5_Khartoum_Roads_Test_Public',
               'AOI_3_Paris_Roads_Test_Public','AOI_4_Shanghai_Roads_Test_Public']
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Test_Public', 'AOI_5_Khartoum_Roads_Test_Public','AOI_3_Paris_Roads_Test_Public', 'AOI_4_Shanghai_Roads_Test_Public'],
                  'vegas':['AOI_2_Vegas_Roads_Test_Public'],
                  'paris':['AOI_3_Paris_Roads_Test_Public'],
                  'shanghai':['AOI_4_Shanghai_Roads_Test_Public'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Test_Public']}     
    
    # select the images
    sample_df = meta_df[(meta_df.img_files.isin(test_folders))
                        &(meta_df.width == preset_dict[preset]['width'])
                        &(meta_df.channels == preset_dict[preset]['channel_count'])
                        &(meta_df.img_folders == preset_dict[preset]['subfolder'])
                        &(meta_df.img_files.isin(cities_dict[city]))]                       

    # get the data as lists for simplicity
    or_imgs = list(sample_df[['img_subfolders','img_files','img_folders']]
                   .apply(lambda row: os.path.join(path_prefix,row['img_files'],row['img_folders']+'_8bit',row['img_subfolders']), axis=1).values)

    le, u = sample_df['img_folders'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    city_folders = list(sample_df.img_files.values)
    img_names = list(sample_df.img_subfolders.values)
    
    return or_imgs,city_folders,img_names,cty_no,path_prefix

# high level function that return list of images and cities under presets
def get_train_dataset(preset,
                     preset_dict,
                     city='all',
                     path_prefix=''):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Train', 'AOI_5_Khartoum_Roads_Train','AOI_3_Paris_Roads_Train', 'AOI_4_Shanghai_Roads_Train'],
                  'vegas':['AOI_2_Vegas_Roads_Train'],
                  'paris':['AOI_3_Paris_Roads_Train'],
                  'shanghai':['AOI_4_Shanghai_Roads_Train'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Train']}    
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_folder.isin(cities_dict[city]))]

    # get the data as lists for simplicity
    bit8_imgs = list(sample_df.bit8_path.values)
    bit8_masks = list(sample_df.mask_path.values)
    bit8_imgs = [(os.path.join(path_prefix,path)) for path in bit8_imgs]
    bit8_masks = [(os.path.join(path_prefix,path)) for path in bit8_masks]
    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    return bit8_imgs,bit8_masks,cty_no

# dataset class
class SatellitesDataset(data.Dataset):
    def __init__(self,
                 preset,
                 image_paths = [],
                 mask_paths = None,                 
                 transforms = None,
                 ):
        
        self.mask_paths = mask_paths
        self.preset = preset
        self.transforms = transforms
        
        if mask_paths is not None:
            self.image_paths = sorted(image_paths)
            self.mask_paths = sorted(mask_paths)

            if len(self.image_paths) != len(mask_paths):
                raise ValueError('Mask list length <> image list lenth')
            if [path.split('/')[4].split('img')[1].split('.')[0] for path in self.image_paths] != [path.split('/')[4].split('img')[1].split('.')[0] for path in self.mask_paths]:            
                 raise ValueError('Mask list sorting <> image list sorting')
        else:
            self.image_paths = image_paths
            # self.image_paths = sorted(image_paths)
                
    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        if self.mask_paths is not None: 

            img = imread(self.image_paths[idx])
            target_channels = np.zeros(shape=(self.preset['width'],self.preset['width'],len(self.preset['channels'])))
            
            # expand grayscale images to 3 dimensions
            if len(img.shape)<3:
                img = np.expand_dims(img, 2)                
            
            for i,channel in enumerate(self.preset['channels']):
                target_channels[:,:,i] = img[:,:,channel-1]
            
            target_channels = target_channels.astype('uint8')
            
            mask = imread(self.mask_paths[idx])
            mask = mask.astype('uint8')
            
            if self.transforms is not None:
                 target_channels, mask = self.transforms(target_channels, mask)
            
            return target_channels,mask                    

        else:
            img = imread(self.image_paths[idx])
            target_channels = np.zeros(shape=(self.preset['width'],self.preset['width'],len(self.preset['channels'])))
            
            for i,channel in enumerate(self.preset['channels']):
                target_channels[:,:,i] = img[:,:,channel-1]
            
            target_channels = target_channels.astype('uint8')
            
            if self.transforms is not None:
                 target_channels, _ = self.transforms(target_channels, None)
            return target_channels

def get_train_dataset_for_predict(preset,
                                  preset_dict,
                                  city='all'):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Train', 'AOI_5_Khartoum_Roads_Train','AOI_3_Paris_Roads_Train', 'AOI_4_Shanghai_Roads_Train'],
                  'vegas':['AOI_2_Vegas_Roads_Train'],
                  'paris':['AOI_3_Paris_Roads_Train'],
                  'shanghai':['AOI_4_Shanghai_Roads_Train'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Train']}     
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_folder.isin(cities_dict[city]))]                       
    
    # get the data as lists for simplicity
    bit8_imgs = list(sample_df.bit8_path.values)
    bit8_imgs = [(os.path.join(prefix_train,path)) for path in bit8_imgs]

    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    city_folders = list(sample_df.img_folder.values)
    img_names = list(sample_df.img_file.values)    
    
    return bit8_imgs,city_folders,img_names,cty_no,prefix   

def get_train_dataset_wide_masks(preset,
                     preset_dict):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')

    # filter out bad new masks
    new_mask_df = pd.read_csv(wide_mask_df_file)
    good_new_masks = list(new_mask_df[new_mask_df.correct == 1].img_names.values)
    
    # filter only roads with mostly non-paved roads 
    
    df = pd.read_csv('geojson_df_full.csv')
    table = pd.pivot_table(df,
                   index=["img_id"],
                   columns = ['paved'],
                   values=["linestring"],
                   aggfunc={len},fill_value=0)
    table.columns = ['count_paved','count_non_paved'] 
    mostly_non_paved_imgs = list(table[table.count_paved < table.count_non_paved].index.values)    
    
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        &(data_df.mask_max > 0) # filter broken masks
                        &(data_df.channels == preset_dict[preset]['channel_count']) # preset filter
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder']) # preset filter
                        &(data_df.img_file.isin(good_new_masks) # filter new good masks
                        &(data_df['img_subfolders']
                          .apply(lambda x: 'AOI'+x.split('AOI')[1][:-4])
                          .isin(mostly_non_paved_imgs)) # filter out mostly paved roads
                         )
                       ]

    # get the data as lists for simplicity
    bit8_imgs = list(sample_df.bit8_path.values)
    bit8_masks = list(sample_df.mask_path.values)
    
    # replace masks with width masks
    bit8_masks = [(path.replace("_mask","_width_mask")) for path in bit8_masks]
    
    bit8_imgs = [(os.path.join(prefix_train,path)) for path in bit8_imgs]
    bit8_masks = [(os.path.join(prefix_train,path)) for path in bit8_masks]
    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    return bit8_imgs,bit8_masks,cty_no

def get_train_dataset_layered_masks(preset,
                     preset_dict):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')

    # note that I am removing wide masks - because layered masks with zero pixels somehow passed my filter
    new_mask_df = pd.read_csv(wide_mask_df_file)
    good_new_masks = list(new_mask_df[new_mask_df.correct == 1].img_names.values)
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_file.isin(good_new_masks))
                       ]

    # get the data as lists for simplicity
    bit8_imgs = list(sample_df.bit8_path.values)
    bit8_masks = list(sample_df.mask_path.values)
    
    # replace masks with width masks
    bit8_masks = [(path.replace("_mask","_layered_mask")) for path in bit8_masks]
    
    bit8_imgs = [(os.path.join(prefix_train,path)) for path in bit8_imgs]
    bit8_masks = [(os.path.join(prefix_train,path)) for path in bit8_masks]
    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    return bit8_imgs,bit8_masks,cty_no

# high level function that return list of images and cities under presets
def get_train_dataset_all(preset,
                     preset_dict,
                     city='all'):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Train', 'AOI_5_Khartoum_Roads_Train','AOI_3_Paris_Roads_Train', 'AOI_4_Shanghai_Roads_Train'],
                  'vegas':['AOI_2_Vegas_Roads_Train'],
                  'paris':['AOI_3_Paris_Roads_Train'],
                  'shanghai':['AOI_4_Shanghai_Roads_Train'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Train']}    
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        # &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_folder.isin(cities_dict[city]))]

    # get the data as lists for simplicity
    bit8_imgs = list(sample_df.bit8_path.values)
    bit8_masks = list(sample_df.mask_path.values)
    
    bit8_masks = [(path.replace("_mask","_all_mask")) for path in bit8_masks]
    bit8_masks = [(path.replace("RGB-PanSharpen_all_mask/RGB-PanSharpen","MUL-PanSharpen_all_mask/MUL-PanSharpen")) for path in bit8_masks]

    
    bit8_imgs = [(os.path.join(prefix_train,path)) for path in bit8_imgs]
    bit8_masks = [(os.path.join(prefix_train,path)) for path in bit8_masks]
    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    return bit8_imgs,bit8_masks,cty_no

def get_train_dataset_for_predict_all(preset,
                                  preset_dict,
                                  city='all'):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Train', 'AOI_5_Khartoum_Roads_Train','AOI_3_Paris_Roads_Train', 'AOI_4_Shanghai_Roads_Train'],
                  'vegas':['AOI_2_Vegas_Roads_Train'],
                  'paris':['AOI_3_Paris_Roads_Train'],
                  'shanghai':['AOI_4_Shanghai_Roads_Train'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Train']}     
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        # &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_folder.isin(cities_dict[city]))]                       
    
    # get the data as lists for simplicity
    bit8_imgs = list(sample_df.bit8_path.values)
    bit8_imgs = [(os.path.join(prefix_train,path)) for path in bit8_imgs]

    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    city_folders = list(sample_df.img_folder.values)
    img_names = list(sample_df.img_file.values)    
    
    return bit8_imgs,city_folders,img_names,cty_no,prefix
def get_train_dataset_all_16bit(preset,
                     preset_dict,
                     city='all'):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Train', 'AOI_5_Khartoum_Roads_Train','AOI_3_Paris_Roads_Train', 'AOI_4_Shanghai_Roads_Train'],
                  'vegas':['AOI_2_Vegas_Roads_Train'],
                  'paris':['AOI_3_Paris_Roads_Train'],
                  'shanghai':['AOI_4_Shanghai_Roads_Train'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Train']}    
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        # &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_folder.isin(cities_dict[city]))]

    # get the data as lists for simplicity
    bit16_imgs = list(sample_df.img_path.values)
    bit8_masks = list(sample_df.mask_path.values)
    
    bit8_masks = [(path.replace("_mask","_all_mask")) for path in bit8_masks]       
    
    bit16_imgs = [(os.path.join(prefix_train,path)) for path in bit16_imgs]
    bit8_masks = [(os.path.join(prefix_train,path)) for path in bit8_masks]
    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    return bit16_imgs,bit8_masks,cty_no
def get_train_dataset_for_predict_all_16bit(preset,
                                  preset_dict,
                                  city='all'):
    mask_df = pd.read_csv(mask_df_file)
    meta_df = pd.read_csv(meta_data_file)
    data_df = mask_df.merge(meta_df[['img_subfolders','width','channels']], how = 'left', left_on = 'img_file', right_on = 'img_subfolders')
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Train', 'AOI_5_Khartoum_Roads_Train','AOI_3_Paris_Roads_Train', 'AOI_4_Shanghai_Roads_Train'],
                  'vegas':['AOI_2_Vegas_Roads_Train'],
                  'paris':['AOI_3_Paris_Roads_Train'],
                  'shanghai':['AOI_4_Shanghai_Roads_Train'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Train']}     
    
    # select the images
    sample_df = data_df[(data_df.width == preset_dict[preset]['width'])
                        # &(data_df.mask_max > 0)
                        &(data_df.channels == preset_dict[preset]['channel_count'])
                        &(data_df.img_subfolder == preset_dict[preset]['subfolder'])
                        &(data_df.img_folder.isin(cities_dict[city]))]                       
    
    # get the data as lists for simplicity
    bit16_imgs = list(sample_df.img_path.values)
    bit16_imgs = [(os.path.join(prefix_train,path)) for path in bit16_imgs]

    le, u = sample_df['img_folder'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    city_folders = list(sample_df.img_folder.values)
    img_names = list(sample_df.img_file.values)    
    
    return bit16_imgs,city_folders,img_names,cty_no,prefix
def get_test_dataset_16bit(preset,
                     preset_dict,
                     city='all'):
    meta_df = pd.read_csv(meta_data_file)
    
    test_folders = ['AOI_2_Vegas_Roads_Test_Public','AOI_5_Khartoum_Roads_Test_Public',
               'AOI_3_Paris_Roads_Test_Public','AOI_4_Shanghai_Roads_Test_Public']
    
    cities_dict = {'all': ['AOI_2_Vegas_Roads_Test_Public', 'AOI_5_Khartoum_Roads_Test_Public','AOI_3_Paris_Roads_Test_Public', 'AOI_4_Shanghai_Roads_Test_Public'],
                  'vegas':['AOI_2_Vegas_Roads_Test_Public'],
                  'paris':['AOI_3_Paris_Roads_Test_Public'],
                  'shanghai':['AOI_4_Shanghai_Roads_Test_Public'],
                  'khartoum': ['AOI_5_Khartoum_Roads_Test_Public']}     
    
    # select the images
    sample_df = meta_df[(meta_df.img_files.isin(test_folders))
                        &(meta_df.width == preset_dict[preset]['width'])
                        &(meta_df.channels == preset_dict[preset]['channel_count'])
                        &(meta_df.img_folders == preset_dict[preset]['subfolder'])
                        &(meta_df.img_files.isin(cities_dict[city]))]                       

    # get the data as lists for simplicity
    or_imgs = list(sample_df[['img_subfolders','img_files','img_folders']]
                   .apply(lambda row: os.path.join(prefix,row['img_files'],row['img_folders'],row['img_subfolders']), axis=1).values)

    le, u = sample_df['img_folders'].factorize()
    sample_df.loc[:,'city_no'] = le
    cty_no = list(sample_df.city_no.values)
    
    city_folders = list(sample_df.img_files.values)
    img_names = list(sample_df.img_subfolders.values)
    
    return or_imgs,city_folders,img_names,cty_no,prefix