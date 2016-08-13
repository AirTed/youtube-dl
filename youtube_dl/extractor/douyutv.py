# coding: utf-8
from __future__ import unicode_literals

import hashlib
import time
import uuid
from .common import InfoExtractor
from ..utils import (ExtractorError, unescapeHTML, sanitized_Request)
from ..compat import (compat_str, compat_basestring, compat_urllib_parse_urlencode)


class DouyuTVIE(InfoExtractor):
    IE_DESC = '斗鱼'
    _VALID_URL = r'https?://(?:www\.)?douyu(?:tv)?\.com/(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'http://www.douyutv.com/iseven',
        'info_dict': {
            'id': '17732',
            'display_id': 'iseven',
            'ext': 'flv',
            'title': 're:^清晨醒脑！T-ara根本停不下来！ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 're:.*m7show@163\.com.*',
            'thumbnail': 're:^https?://.*\.jpg$',
            'uploader': '7师傅',
            'uploader_id': '431925',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.douyutv.com/85982',
        'info_dict': {
            'id': '85982',
            'display_id': '85982',
            'ext': 'flv',
            'title': 're:^小漠从零单排记！——CSOL2躲猫猫 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:746a2f7a253966a06755a912f0acc0d2',
            'thumbnail': 're:^https?://.*\.jpg$',
            'uploader': 'douyu小漠',
            'uploader_id': '3769985',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Room not found',
    }, {
        'url': 'http://www.douyutv.com/17732',
        'info_dict': {
            'id': '17732',
            'display_id': '17732',
            'ext': 'flv',
            'title': 're:^清晨醒脑！T-ara根本停不下来！ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 're:.*m7show@163\.com.*',
            'thumbnail': 're:^https?://.*\.jpg$',
            'uploader': '7师傅',
            'uploader_id': '431925',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.douyu.com/xiaocang',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if video_id.isdigit():
            room_id = video_id
        else:
            page = self._download_webpage(url, video_id)
            room_id = self._html_search_regex(
                r'"room_id"\s*:\s*(\d+),', page, 'room id')

        flv_info_json = None
        # Douyu API sometimes returns error "Unable to load the requested class: eticket_redis_cache"
        # Retry with different parameters - same parameters cause same errors
        for i in range(5):
            tt = int(time.time() / 60)
            did = uuid.uuid4().hex.upper()

            sign_content = '{room_id}{did}A12Svb&%1UUmf@hC{tt}'.format(room_id = room_id, did = did, tt = tt)
            sign = hashlib.md5((sign_content).encode('utf-8')).hexdigest()

            payload = {'cdn': 'ws', 'rate': '0', 'tt': tt, 'did': did, 'sign': sign}
            flv_info_data = compat_urllib_parse_urlencode(payload)

            flv_info_request_url = 'http://www.douyu.com/lapi/live/getPlay/%s' % room_id
            flv_info_request = sanitized_Request(flv_info_request_url, flv_info_data,
                {'Content-Type': 'application/x-www-form-urlencoded'})

            flv_info_content = self._download_webpage(flv_info_request, video_id)
            try:
                flv_info_json = self._parse_json(flv_info_content, video_id, fatal=False)
            except ExtractorError:
                # Wait some time before retrying to get a different time() value
                self._sleep(1, video_id, msg_template='%(video_id)s: Error occurs. '
                                                      'Waiting for %(timeout)s seconds before retrying')
                continue
            else:
                break
        if flv_info_json is None:
            raise ExtractorError('Unable to fetch API result')

        room_url = 'http://m.douyu.com/html5/live?roomId=%s' % room_id
        room_content = self._download_webpage(room_url, video_id)
        room_json = self._parse_json(room_content, video_id, fatal=False)

        room = room_json['data']
        flv_info = flv_info_json['data']

        show_status = room.get('show_status')
        # 1 = live, 2 = offline
        if show_status == '2':
            raise ExtractorError(
                'Live stream is offline', expected=True)

        error_code = flv_info_json.get('error', 0)
        if error_code is not 0:
            error_desc = 'Server reported error %i' % error_code
            if isinstance(flv_info, (compat_str, compat_basestring)):
                error_desc += ': ' + flv_info
            raise ExtractorError(error_desc, expected=True)

        base_url = flv_info['rtmp_url']
        live_path = flv_info['rtmp_live']

        video_url = '%s/%s' % (base_url, live_path)

        title = self._live_title(unescapeHTML(room['room_name']))
        description = room.get('notice')
        thumbnail = room.get('room_src')
        uploader = room.get('nickname')

        return {
            'id': room_id,
            'display_id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'is_live': True,
        }
