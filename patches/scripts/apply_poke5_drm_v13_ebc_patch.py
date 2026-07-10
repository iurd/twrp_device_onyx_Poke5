#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
path = root / "bootable/recovery/minuitwrp/graphics_drm.cpp"
text = path.read_text()
changed = False

if "#include <errno.h>" not in text:
    text = text.replace("#include <drm_fourcc.h>\n", "#include <drm_fourcc.h>\n#include <errno.h>\n", 1)
    changed = True

anchor = "static int drm_fd = -1;\n"
ebc_block = r'''

#define ONYX_EBC_GET_BUFFER_INFO 0x7003
#define ONYX_EBC_SEND_UPDATE 0x700c
#define ONYX_EBC_AUTO_TEMP 0x1000
#define ONYX_EBC_DITHER_FLAG 0x20000

struct poke5_ebc_buffer_info {
    uint32_t words[14];
};

struct poke5_ebc_update {
    uint32_t left;
    uint32_t top;
    uint32_t width;
    uint32_t height;
    uint32_t waveform_mode;
    uint32_t update_mode;
    uint32_t update_marker;
    int32_t temperature;
    uint32_t flags;
};

static int ebc_fd = -1;
static uint8_t *ebc_buffer = nullptr;
static size_t ebc_buffer_size = 0;
static uint32_t ebc_width = 0;
static uint32_t ebc_height = 0;
static uint32_t ebc_update_marker = 1;

static bool onyx_ebc_try_init(uint32_t request_width, uint32_t request_height) {
    struct poke5_ebc_buffer_info info = {};
    int fd = open("/dev/ebc", O_RDWR);
    if (fd < 0) {
        perror("Poke5 EBC: open /dev/ebc failed");
        return false;
    }

    int info_size = ioctl(fd, ONYX_EBC_GET_BUFFER_INFO, nullptr);
    printf("Poke5 EBC: null GET_BUFFER_INFO returned %d for request %ux%u\n",
           info_size, request_width, request_height);
    if (info_size != 0 && info_size != (int)sizeof(info)) {
        close(fd);
        return false;
    }

    info.words[6] = request_width;
    info.words[7] = request_height;
    if (ioctl(fd, ONYX_EBC_GET_BUFFER_INFO, &info) < 0) {
        perror("Poke5 EBC: GET_BUFFER_INFO failed");
        close(fd);
        return false;
    }

    uint32_t width = info.words[6];
    uint32_t height = info.words[7];
    printf("Poke5 EBC: request %ux%u got words[6,7]=%ux%u words[0..5]=%u,%u,%u,%u,%u,%u\n",
           request_width, request_height, width, height,
           info.words[0], info.words[1], info.words[2], info.words[3], info.words[4], info.words[5]);

    if (width == 0 || height == 0 || width > 4096 || height > 4096) {
        close(fd);
        return false;
    }

    size_t size = (size_t)width * height * 4;
    uint8_t *buffer = static_cast<uint8_t *>(mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0));
    if (buffer == MAP_FAILED) {
        perror("Poke5 EBC: mmap failed");
        close(fd);
        return false;
    }

    ebc_fd = fd;
    ebc_buffer = buffer;
    ebc_buffer_size = size;
    ebc_width = width;
    ebc_height = height;
    printf("Poke5 EBC: mapped %ux%u buffer size=%zu\n", ebc_width, ebc_height, ebc_buffer_size);
    return true;
}

static bool onyx_ebc_init(uint32_t drm_width, uint32_t drm_height) {
    const uint32_t candidates[][2] = {
        {drm_width, drm_height},
        {1448, 1072},
        {1072, 1448},
        {1872, 1404},
        {1404, 1872},
        {407, 1083},
        {1083, 407},
    };

    if (ebc_fd >= 0)
        return true;

    for (size_t i = 0; i < sizeof(candidates) / sizeof(candidates[0]); ++i) {
        if (onyx_ebc_try_init(candidates[i][0], candidates[i][1]))
            return true;
    }
    printf("Poke5 EBC: failed to initialize any candidate buffer\n");
    return false;
}

static int onyx_ebc_flip(const GRSurface *surface) {
    if (ebc_fd < 0 || !ebc_buffer || !surface)
        return -ENODEV;
    if ((uint32_t)surface->width != ebc_width || (uint32_t)surface->height != ebc_height) {
        printf("Poke5 EBC: surface %dx%d does not match EBC %ux%u\n",
               surface->width, surface->height, ebc_width, ebc_height);
        return -EINVAL;
    }

    const size_t packed_row_bytes = (size_t)surface->width * 4;
    for (uint32_t y = 0; y < (uint32_t)surface->height; ++y) {
        memcpy(ebc_buffer + y * packed_row_bytes,
               surface->data + y * surface->row_bytes,
               packed_row_bytes);
    }

    struct poke5_ebc_update update = {};
    update.left = 0;
    update.top = 0;
    update.width = surface->width;
    update.height = surface->height;
    update.waveform_mode = 5;
    update.update_mode = 1;
    update.update_marker = ebc_update_marker++;
    update.temperature = ONYX_EBC_AUTO_TEMP;
    update.flags = ONYX_EBC_DITHER_FLAG;

    int ret = ioctl(ebc_fd, ONYX_EBC_SEND_UPDATE, &update);
    printf("Poke5 EBC: SEND_UPDATE ret=%d marker=%u rect=[%u %u %u %u] waveform=%u update=%u temp=0x%x flags=0x%x\n",
           ret, update.update_marker, update.left, update.top, update.width, update.height,
           update.waveform_mode, update.update_mode, update.temperature, update.flags);
    if (ret < 0)
        perror("Poke5 EBC: SEND_UPDATE failed");
    return ret;
}
'''
if ebc_block.strip() not in text:
    if anchor not in text:
        raise SystemExit("Expected drm_fd anchor not found")
    text = text.replace(anchor, anchor + ebc_block, 1)
    changed = True

old_dim = '''    width = main_monitor_crtc->mode.hdisplay;
    height = main_monitor_crtc->mode.vdisplay;
'''
new_dim = '''    width = main_monitor_crtc->mode.hdisplay;
    height = main_monitor_crtc->mode.vdisplay;
    if (main_monitor_connector &&
            main_monitor_connector->connector_type == DRM_MODE_CONNECTOR_DSI &&
            main_monitor_connector->connector_type_id == 2 &&
            onyx_ebc_init(width, height)) {
        printf("Poke5 EBC: override minui surface from DRM %ux%u to EBC %ux%u\\n",
               width, height, ebc_width, ebc_height);
        width = ebc_width;
        height = ebc_height;
    }
'''
if "Poke5 EBC: override minui surface" not in text:
    if old_dim not in text:
        raise SystemExit("Expected width/height assignment not found")
    text = text.replace(old_dim, new_dim, 1)
    changed = True

old_init_commit = '''    drm_enable_crtc(drm_fd, main_monitor_crtc, drm_surfaces[1]);
'''
new_init_commit = '''    if (ebc_fd < 0) {
        drm_enable_crtc(drm_fd, main_monitor_crtc, drm_surfaces[1]);
    } else {
        printf("Poke5 EBC: skip initial DRM CRTC commit; EBC handles refresh\\n");
    }
'''
if old_init_commit in text:
    text = text.replace(old_init_commit, new_init_commit, 1)
    changed = True
elif "Poke5 EBC: skip initial DRM CRTC commit" not in text:
    # v7 may already have replaced the call; tolerate and handle flip only.
    pass

flip_start = text.index("static GRSurface* drm_flip")
flip_end = text.index("static void drm_exit", flip_start)
flip_block = r'''static GRSurface* drm_flip(minui_backend* backend __unused) {
    int ret;

    memcpy(drm_surfaces[current_buffer]->base.data,
            draw_buf->data, draw_buf->height * draw_buf->row_bytes);

    if (ebc_fd >= 0) {
        ret = onyx_ebc_flip(draw_buf);
        if (ret < 0) {
            printf("Poke5 EBC flip failed ret=%d; keeping UI alive\n", ret);
            return draw_buf;
        }
        return draw_buf;
    }

    ret = drmModePageFlip(drm_fd, main_monitor_crtc->crtc_id,
                          drm_surfaces[current_buffer]->fb_id, 0, NULL);
    if (ret < 0) {
        printf("drmModePageFlip failed ret=%d\n", ret);
        return NULL;
    }
    current_buffer = 1 - current_buffer;
    return draw_buf;
}

'''
if text[flip_start:flip_end] != flip_block:
    text = text[:flip_start] + flip_block + text[flip_end:]
    changed = True

exit_anchor = '''static void drm_exit(minui_backend* backend __unused) {
'''
exit_insert = '''static void drm_exit(minui_backend* backend __unused) {
    if (ebc_buffer) {
        munmap(ebc_buffer, ebc_buffer_size);
        ebc_buffer = nullptr;
        ebc_buffer_size = 0;
    }
    if (ebc_fd >= 0) {
        close(ebc_fd);
        ebc_fd = -1;
    }
'''
if "if (ebc_buffer)" not in text:
    if exit_anchor not in text:
        raise SystemExit("Expected drm_exit anchor not found")
    text = text.replace(exit_anchor, exit_insert, 1)
    changed = True

if changed:
    path.write_text(text)
    print(f"Applied/updated Poke5 DRM v13 EBC patch in {path}")
else:
    print("Poke5 DRM v13 EBC patch already applied")
