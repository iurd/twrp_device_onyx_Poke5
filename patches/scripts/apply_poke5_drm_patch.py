#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
path = root / "bootable/recovery/minuitwrp/graphics_drm.cpp"
text = path.read_text()
changed = False

old1 = '''    if (ret)
        printf("drmModeSetCrtc failed ret=%d\\n", ret);
'''
new1 = '''    if (ret) {
        printf("drmModeSetCrtc failed ret=%d connector=%u crtc=%u fb=%u mode=%ux%u@%u\\n",
               ret,
               main_monitor_connector ? main_monitor_connector->connector_id : 0,
               crtc ? crtc->crtc_id : 0,
               surface ? surface->fb_id : 0,
               main_monitor_crtc->mode.hdisplay,
               main_monitor_crtc->mode.vdisplay,
               main_monitor_crtc->mode.vrefresh);
    }
'''
if old1 in text:
    text = text.replace(old1, new1, 1)
    changed = True
elif "drmModeSetCrtc failed ret=%d connector=%u" not in text:
    raise SystemExit("Expected drmModeSetCrtc snippet not found")

old2 = '''    main_monitor_crtc->mode = main_monitor_connector->modes[selected_mode];

    width = main_monitor_crtc->mode.hdisplay;
'''
new2 = '''    main_monitor_crtc->mode = main_monitor_connector->modes[selected_mode];

    printf("Poke5 DRM debug: connector=%u type=%u type_id=%u enc=%u crtc=%u selected_mode=%u count_modes=%d mode=%ux%u@%u\\n",
           main_monitor_connector->connector_id, main_monitor_connector->connector_type,
           main_monitor_connector->connector_type_id, main_monitor_connector->encoder_id,
           main_monitor_crtc->crtc_id, selected_mode, main_monitor_connector->count_modes,
           main_monitor_crtc->mode.hdisplay, main_monitor_crtc->mode.vdisplay, main_monitor_crtc->mode.vrefresh);

    width = main_monitor_crtc->mode.hdisplay;
'''
old2_previous = '''    printf("Poke5 DRM debug: connector=%u type=%u enc=%u crtc=%u selected_mode=%u count_modes=%d mode=%ux%u@%u\\n",
           main_monitor_connector->connector_id, main_monitor_connector->connector_type,
           main_monitor_connector->encoder_id, main_monitor_crtc->crtc_id,
           selected_mode, main_monitor_connector->count_modes,
           main_monitor_crtc->mode.hdisplay, main_monitor_crtc->mode.vdisplay, main_monitor_crtc->mode.vrefresh);
'''
new2_previous = '''    printf("Poke5 DRM debug: connector=%u type=%u type_id=%u enc=%u crtc=%u selected_mode=%u count_modes=%d mode=%ux%u@%u\\n",
           main_monitor_connector->connector_id, main_monitor_connector->connector_type,
           main_monitor_connector->connector_type_id, main_monitor_connector->encoder_id,
           main_monitor_crtc->crtc_id, selected_mode, main_monitor_connector->count_modes,
           main_monitor_crtc->mode.hdisplay, main_monitor_crtc->mode.vdisplay, main_monitor_crtc->mode.vrefresh);
'''
if old2 in text:
    text = text.replace(old2, new2, 1)
    changed = True
elif old2_previous in text:
    text = text.replace(old2_previous, new2_previous, 1)
    changed = True
elif "Poke5 DRM debug: connector=%u type=%u type_id=%u" not in text:
    raise SystemExit("Expected Poke5 DRM debug insertion point not found")

connector_block = r'''static const char* drm_connector_type_name(unsigned type) {
    switch (type) {
        case DRM_MODE_CONNECTOR_DSI:
            return "DSI";
        case DRM_MODE_CONNECTOR_eDP:
            return "eDP";
        case DRM_MODE_CONNECTOR_LVDS:
            return "LVDS";
        case DRM_MODE_CONNECTOR_HDMIA:
            return "HDMI-A";
        case DRM_MODE_CONNECTOR_HDMIB:
            return "HDMI-B";
        default:
            return NULL;
    }
}

static bool connector_enabled_by_sysfs(drmModeConnector *connector) {
    const char *type_name = drm_connector_type_name(connector->connector_type);
    char path[128];
    char value[32] = {0};
    int fd;
    ssize_t n;

    if (!type_name)
        return false;

    snprintf(path, sizeof(path), "/sys/class/drm/card0-%s-%u/enabled",
             type_name, connector->connector_type_id);
    fd = open(path, O_RDONLY);
    if (fd < 0)
        return false;
    n = read(fd, value, sizeof(value) - 1);
    close(fd);
    if (n <= 0)
        return false;

    printf("Poke5 DRM sysfs enabled connector id=%u name=%s-%u enabled=%s",
           connector->connector_id, type_name, connector->connector_type_id, value);
    return strncmp(value, "enabled", 7) == 0;
}

static bool connector_is_poke5_epdc(drmModeConnector *connector) {
    return connector->connector_type == DRM_MODE_CONNECTOR_DSI &&
           connector->connector_type_id == 2 &&
           connector->connection == DRM_MODE_CONNECTED &&
           connector->count_modes > 0;
}

static drmModeConnector *find_used_connector_by_type(int fd,
                                 drmModeRes *resources,
                                 unsigned type) {
    int i;

    for (i = 0; i < resources->count_connectors; i++) {
        drmModeConnector *connector = drmModeGetConnector(fd, resources->connectors[i]);
        if (connector) {
            if ((connector->connector_type == type) && connector_is_poke5_epdc(connector)) {
                printf("Poke5 DRM forced EPDC connector id=%u type=%u type_id=%u\n",
                       connector->connector_id, connector->connector_type, connector->connector_type_id);
                return connector;
            }
            drmModeFreeConnector(connector);
        }
    }

    for (i = 0; i < resources->count_connectors; i++) {
        drmModeConnector *connector = drmModeGetConnector(fd, resources->connectors[i]);
        if (connector) {
            if ((connector->connector_type == type) &&
                    (connector->connection == DRM_MODE_CONNECTED) &&
                    (connector->count_modes > 0) &&
                    connector_enabled_by_sysfs(connector)) {
                printf("Poke5 DRM selected enabled connector id=%u type=%u type_id=%u\n",
                       connector->connector_id, connector->connector_type, connector->connector_type_id);
                return connector;
            }
            drmModeFreeConnector(connector);
        }
    }

    for (i = 0; i < resources->count_connectors; i++) {
        drmModeConnector *connector = drmModeGetConnector(fd, resources->connectors[i]);
        if (connector) {
            if ((connector->connector_type == type) &&
                    (connector->connection == DRM_MODE_CONNECTED) &&
                    (connector->count_modes > 0)) {
                printf("Poke5 DRM fallback selected connector id=%u type=%u type_id=%u\n",
                       connector->connector_id, connector->connector_type, connector->connector_type_id);
                return connector;
            }

            drmModeFreeConnector(connector);
        }
    }
    return NULL;
}

static drmModeConnector *find_first_connected_connector(int fd,
                             drmModeRes *resources) {
    int i;

    for (i = 0; i < resources->count_connectors; i++) {
        drmModeConnector *connector = drmModeGetConnector(fd, resources->connectors[i]);
        if (connector) {
            if (connector_is_poke5_epdc(connector)) {
                printf("Poke5 DRM forced first EPDC connector id=%u type=%u type_id=%u\n",
                       connector->connector_id, connector->connector_type, connector->connector_type_id);
                return connector;
            }
            drmModeFreeConnector(connector);
        }
    }

    for (i = 0; i < resources->count_connectors; i++) {
        drmModeConnector *connector = drmModeGetConnector(fd, resources->connectors[i]);
        if (connector) {
            if ((connector->count_modes > 0) &&
                    (connector->connection == DRM_MODE_CONNECTED) &&
                    connector_enabled_by_sysfs(connector)) {
                printf("Poke5 DRM sysfs enabled first connector id=%u type=%u type_id=%u\n",
                       connector->connector_id, connector->connector_type, connector->connector_type_id);
                return connector;
            }
            drmModeFreeConnector(connector);
        }
    }

    for (i = 0; i < resources->count_connectors; i++) {
        drmModeConnector *connector = drmModeGetConnector(fd, resources->connectors[i]);
        if (connector) {
            if ((connector->count_modes > 0) &&
                    (connector->connection == DRM_MODE_CONNECTED))
                return connector;

            drmModeFreeConnector(connector);
        }
    }
    return NULL;
}

'''

if "static const char* drm_connector_type_name" in text:
    start = text.index("static const char* drm_connector_type_name")
else:
    start = text.index("static drmModeConnector *find_used_connector_by_type")
end = text.index("static drmModeConnector *find_main_monitor", start)
old_block = text[start:end]
if old_block != connector_block:
    text = text[:start] + connector_block + text[end:]
    changed = True

crtc_marker = '''    /*
     * Find the encoder. If we already have one, just use it.
     */
'''
crtc_force = '''    if (connector && connector->connector_type == DRM_MODE_CONNECTOR_DSI &&
            connector->connector_type_id == 2 && resources->count_crtcs > 1) {
        printf("Poke5 DRM forced EPDC crtc index=1 id=%u for connector id=%u type_id=%u\\n",
               resources->crtcs[1], connector->connector_id, connector->connector_type_id);
        return drmModeGetCrtc(fd, resources->crtcs[1]);
    }

'''
if "Poke5 DRM forced EPDC crtc index=1" not in text:
    if crtc_marker not in text:
        raise SystemExit("Expected find_crtc marker not found")
    text = text.replace(crtc_marker, crtc_force + crtc_marker, 1)
    changed = True

flip_start = text.index("static GRSurface* drm_flip")
flip_end = text.index("static void drm_exit", flip_start)
flip_block = r'''static GRSurface* drm_flip(minui_backend* backend __unused) {
    static int poke5_skip_pageflip_count = 0;
    int ret;

    memcpy(drm_surfaces[current_buffer]->base.data,
            draw_buf->data, draw_buf->height * draw_buf->row_bytes);

    if (main_monitor_connector &&
            main_monitor_connector->connector_type == DRM_MODE_CONNECTOR_DSI &&
            main_monitor_connector->connector_type_id == 2) {
        if (poke5_skip_pageflip_count < 8) {
            printf("Poke5 DRM v6: skip drmModePageFlip for EPDC connector=%u crtc=%u fb=%u frame=%d\n",
                   main_monitor_connector->connector_id,
                   main_monitor_crtc ? main_monitor_crtc->crtc_id : 0,
                   drm_surfaces[current_buffer] ? drm_surfaces[current_buffer]->fb_id : 0,
                   poke5_skip_pageflip_count);
        }
        poke5_skip_pageflip_count++;
        return draw_buf;
    }

    ret = drmModePageFlip(drm_fd, main_monitor_crtc->crtc_id,
                          drm_surfaces[current_buffer]->fb_id, 0, NULL);
    if (ret < 0) {
        int setret;
        printf("drmModePageFlip failed ret=%d, fallback drmModeSetCrtc and keep UI alive\n", ret);
        setret = drmModeSetCrtc(drm_fd, main_monitor_crtc->crtc_id,
                                drm_surfaces[current_buffer]->fb_id,
                                0, 0,
                                &main_monitor_connector->connector_id,
                                1,
                                &main_monitor_crtc->mode);
        if (setret < 0) {
            printf("fallback drmModeSetCrtc failed ret=%d\n", setret);
        } else {
            current_buffer = 1 - current_buffer;
        }
        return draw_buf;
    }
    current_buffer = 1 - current_buffer;
    return draw_buf;
}

'''
old_flip_block = text[flip_start:flip_end]
if old_flip_block != flip_block:
    text = text[:flip_start] + flip_block + text[flip_end:]
    changed = True

if changed:
    path.write_text(text)
    print(f"Applied/updated Poke5 DRM v6 patch in {path}")
else:
    print("Poke5 DRM v6 patch already applied")
