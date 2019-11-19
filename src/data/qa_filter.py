import itertools

def get_good_qa_ints_to_keep_l2qa():
    """
    https://ecostress.jpl.nasa.gov/downloads/psd/ECOSTRESS_SDS_PSD_L2_ver1-1.pdf for qa flag bits
    """

    good_lst_accuracy_flags = ["11", "10"]

    emissivity_accuracy_flags = ["11", "10"]

    iterations_quality_flag = ["11", "10", "01", "00"]
    ao_quality_flag = ["11", "10", "01", "00"]
    mmd_quality_flag = ["11", "10", "01", "00"]

    data_quality_flag = "00" # only best
    mandatory_qa_flag = "00" # only best
    unused_cloud_flag = "00"

    good_bin_strs_for_masking = []
    good_ints_for_masking = []

    accuracy_flags = list(map(list, itertools.product(emissivity_accuracy_flags, good_lst_accuracy_flags , repeat=1)))
    model_flags = list(map(list, itertools.product(iterations_quality_flag, ao_quality_flag, mmd_quality_flag, repeat=1)))

    for i in accuracy_flags:
        for j in model_flags:
            good_bin_strs_for_masking.append(mandatory_qa_flag + data_quality_flag + unused_cloud_flag + "".join(j) + "".join(i))

    for i in good_bin_strs_for_masking:
        good_ints_for_masking.append(int(i, 2))
    
    return good_ints_for_masking

def get_good_qa_ints_to_keep_l2cloud():
    """
    https://ecostress.jpl.nasa.gov/downloads/psd/ECOSTRESS_SDS_PSD_L2_ver1-1.pdf for qa flag bits
    """

    cloud_mask_flag = ["0", "1"] # 1 is determined, 0 is not determined

    cloud_flag = "0" # 0 is no 1 is yes, either bit 2 3 or 4 set

    thermal_brightness_test = "0" # 0 is no for all these
    thermal_diff_test_b45 = "0"
    thermal_diff_test_b25 = "0"

    landwater_flag = ["0", "1"] # 0 is land 1 is water

    good_bin_strs_for_masking = [
        cloud_mask_flag[0] + cloud_flag + thermal_brightness_test + thermal_diff_test_b45 + thermal_diff_test_b25 + landwater_flag[0],
        cloud_mask_flag[1] + cloud_flag + thermal_brightness_test + thermal_diff_test_b45 + thermal_diff_test_b25 + landwater_flag[0],
        cloud_mask_flag[0] + cloud_flag + thermal_brightness_test + thermal_diff_test_b45 + thermal_diff_test_b25 + landwater_flag[1],
        cloud_mask_flag[1] + cloud_flag + thermal_brightness_test + thermal_diff_test_b45 + thermal_diff_test_b25 + landwater_flag[1]
    ]
    good_ints_for_masking = []

    for i in good_bin_strs_for_masking:
        good_ints_for_masking.append(int(i, 2)) #converts base 2 binary string to int
    
    return good_ints_for_masking

def get_good_qa_ints_to_keep_l3qa():
    """
    https://ecostress.jpl.nasa.gov/downloads/psd/ECOSTRESS_SDS_PSD_L2_ver1-1.pdf for qa flag bits
    """

    raise NotImplemented