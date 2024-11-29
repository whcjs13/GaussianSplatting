#version 300 es
layout(location = 0) in vec2 corner;
layout(location = 1) in vec3 a_center;
layout(location = 2) in vec4 a_col;
layout(location = 3) in vec3 a_covA;
layout(location = 4) in vec3 a_covB;

uniform float W;
uniform float H;
uniform float focal_x;
uniform float focal_y;
uniform float tan_fovx;
uniform float tan_fovy;
uniform float scale_modifier;
uniform mat4 projmatrix;
uniform mat4 viewmatrix;

out vec3 col;
out float depth;
out float scale_modif;
out vec4 con_o;
out vec2 xy;
out vec2 pixf;

vec3 computeCov2D(vec3 mean, float focal_x, float focal_y, float tan_fovx, float tan_fovy, float[6] cov3D, mat4 viewmatrix) {
    vec4 t = viewmatrix * vec4(mean, 1.0);

    float limx = 1.3 * tan_fovx;
    float limy = 1.3 * tan_fovy;
    float txtz = t.x / t.z;
    float tytz = t.y / t.z;
    t.x = min(limx, max(-limx, txtz)) * t.z;
    t.y = min(limy, max(-limy, tytz)) * t.z;

    mat3 J = mat3(
        focal_x / t.z, 0, -(focal_x * t.x) / (t.z * t.z),
        0, focal_y / t.z, -(focal_y * t.y) / (t.z * t.z),
        0, 0, 0
    );

    mat3 W =  mat3(
        viewmatrix[0][0], viewmatrix[1][0], viewmatrix[2][0],
        viewmatrix[0][1], viewmatrix[1][1], viewmatrix[2][1],
        viewmatrix[0][2], viewmatrix[1][2], viewmatrix[2][2]
    );

    mat3 T = W * J;

    mat3 Vrk = mat3(
        cov3D[0], cov3D[1], cov3D[2],
        cov3D[1], cov3D[3], cov3D[4],
        cov3D[2], cov3D[4], cov3D[5]
    );

    mat3 cov = transpose(T) * transpose(Vrk) * T;

    cov[0][0] += .3;
    cov[1][1] += .3;
    return vec3(cov[0][0], cov[0][1], cov[1][1]);
}

float ndc2Pix(float v, float S) {
    return ((v + 1.) * S - 1.) * .5;
}

#define hash33(p) fract(sin( (p) * mat3( 127.1,311.7,74.7 , 269.5,183.3,246.1 , 113.5,271.9,124.6) ) *43758.5453123)

// Original CUDA implementation: https://github.com/graphdeco-inria/diff-gaussian-rasterization/blob/main/cuda_rasterizer/forward.cu#L156
void main() {
	float a_opacity = a_col.w;
    vec3 p_orig = a_center;

    // Transform point by projecting
    vec4 p_hom = projmatrix * viewmatrix * vec4(p_orig, 1);
    float p_w = 1. / (p_hom.w + 1e-7);
    vec3 p_proj = p_hom.xyz * p_w;

    float clip = 1.2 * p_hom.w;
    if (p_hom.z < -clip || p_hom.x < -clip || p_hom.x > clip || p_hom.y < -clip || p_hom.y > clip) {
        gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
        return;
    }


    // Perform near culling, quit if outside.
    vec4 p_view = viewmatrix * vec4(p_orig, 1);
    

    // (Webgl-specific) The covariance matrix is pre-computed on the CPU for faster performance
    float cov3D[6] = float[6](a_covA.x, a_covA.y, a_covA.z, a_covB.x, a_covB.y, a_covB.z);
    // computeCov3D(a_scale, scale_modifier, a_rot, cov3D);

    // Compute 2D screen-space covariance matrix
    vec3 cov = computeCov2D(p_orig, focal_x, focal_y, tan_fovx, tan_fovy, cov3D, viewmatrix);

    // Invert covariance (EWA algorithm)
    float det = (cov.x * cov.z - cov.y * cov.y);
    if (det == 0.) {
        gl_Position = vec4(0, 0, 2, 1);
        return;
    }
    float det_inv = 1. / det;
    vec3 conic = vec3(cov.z, -cov.y, cov.x) * det_inv;

    // Compute extent in screen space (by finding eigenvalues of
    // 2D covariance matrix). Use extent to compute the bounding
    // rectangle of the splat in screen space.

    float mid = 0.5 * (cov.x + cov.z);
    float lambda1 = mid + sqrt(max(0.1, mid * mid - det));
    float lambda2 = mid - sqrt(max(0.1, mid * mid - det));
    float my_radius = ceil(3. * sqrt(max(lambda1, lambda2)));
    vec2 point_image = vec2(ndc2Pix(p_proj.x, W), ndc2Pix(p_proj.y, H));

    // (Webgl-specific) As the covariance matrix is calculated as a one-time operation on CPU in this implementation,
    // we need to apply the scale modifier differently to still allow for real-time scaling of the splats.
    my_radius *= .15 + scale_modifier * .85;
    scale_modif = 1. / scale_modifier;

    // (Webgl-specific) Convert gl_VertexID from [0,1,2,3] to [-1,-1],[1,-1],[-1,1],[1,1]
    
    // Vertex position in screen space
    vec2 screen_pos = point_image + my_radius * corner;

    // Store some useful helper data for the fragment stage
    col = vec3(a_col);
    con_o = vec4(conic, a_opacity);
    xy = point_image;
    pixf = screen_pos;
    depth = p_view.z;

    // (Webgl-specific) Convert from screen-space to clip-space
    vec2 clip_pos = screen_pos / vec2(W, H) * 2. - 1.;
    clip_pos.y = -clip_pos.y;
    gl_Position = vec4(clip_pos, 0, 1);
    //gl_Position = vec4(vec2(p_proj.x, p_proj.y) + corner*my_radius*000000000.1, 0, 1);
}