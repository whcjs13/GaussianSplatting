import numpy as np
from plyfile import PlyData

def compute_cov3d_vectorized(scales, rotations):
    # Scaling matrices
    S = np.stack([np.diag(s) for s in scales])

    # Quaternion to rotation matrices
    r, x, y, z = rotations.T
    
    R = np.empty((len(rotations), 3, 3), dtype=np.float32)
    R[:, 0, 0] = 1.0 - 2.0 * (y * y + z * z)
    R[:, 0, 1] = 2.0 * (x * y - r * z)
    R[:, 0, 2] = 2.0 * (x * z + r * y)
    R[:, 1, 0] = 2.0 * (x * y + r * z)
    R[:, 1, 1] = 1.0 - 2.0 * (x * x + z * z)
    R[:, 1, 2] = 2.0 * (y * z - r * x)
    R[:, 2, 0] = 2.0 * (x * z - r * y)
    R[:, 2, 1] = 2.0 * (y * z + r * x)
    R[:, 2, 2] = 1.0 - 2.0 * (x * x + y * y)

    # Compute M = S * R for each rotation
    M = np.einsum('ijk,ikl->ijl', S, R)

    # Compute Conv Matrix = transpose(M) * M
    M = np.einsum('ijk,ijl->ikl', M, M)

    # Extract covariance components
    covAs = M[:, 0, :3]
    covBs = M[:, 1:, 1:]
    covBs = covBs[:, [0, 0, 1], [0, 1, 1]].reshape(len(M), -1)

    return covAs, covBs


def load_ply(file_path, max_size = -1):    
    plydata = PlyData.read(file_path)
    vertex_data = plydata['vertex']
    if (max_size > 0):
        vertex_data = vertex_data[0:max_size]

    

    # Spherical Harmonics Coefficient
    SH_C0 = 0.28209479177387814

    # Extract positions (x, y, z)
    positions = np.stack([vertex_data['x'], vertex_data['y'], vertex_data['z']], axis=-1)

    # Extract colors
    colors = np.column_stack([
        0.5 + SH_C0 * vertex_data['f_dc_0'],
        0.5 + SH_C0 * vertex_data['f_dc_1'],
        0.5 + SH_C0 * vertex_data['f_dc_2'],
        1 / (1 + np.exp(-vertex_data['opacity']))
    ])

    # Extract scales and rotations
    scales = np.exp(
        np.stack([
            vertex_data['scale_0'], 
            vertex_data['scale_1'], 
            vertex_data['scale_2']
        ], axis=-1)
    )
    rotations = np.stack([
        vertex_data['rot_0'], 
        vertex_data['rot_1'], 
        vertex_data['rot_2'], 
        vertex_data['rot_3']
    ], axis=-1)

    # Compute covariance matrices (vectorized)
    # 데이터 청크 크기 정의
    chunk_size = 100000

    # 스케일과 회전 데이터를 청크로 나누기
    scale_chunks = np.array_split(scales, len(scales) // chunk_size + 1)
    rotation_chunks = np.array_split(rotations, len(rotations) // chunk_size + 1)

    # 결과 저장용 리스트
    covAs_list = []
    covBs_list = []

    # 각 청크에 대해 처리
    for scale_chunk, rotation_chunk in zip(scale_chunks, rotation_chunks):
        covAs_chunk, covBs_chunk = compute_cov3d_vectorized(scale_chunk, rotation_chunk)
        covAs_list.append(covAs_chunk)
        covBs_list.append(covBs_chunk)

    # 청크 결과 합치기
    covAs = np.concatenate(covAs_list, axis=0)
    covBs = np.concatenate(covBs_list, axis=0)

    # Flatten and stack all data
    return np.hstack((positions, colors, covAs, covBs))