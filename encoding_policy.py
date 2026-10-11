"""Source-matched encoding for MP3 merges; no artificial byte budget or retry."""
LEGACY_PROFILE = 'aac-160k-stereo-44100-quicktime-v1'
PROFILE = 'aac-source-matched-quicktime-v3'
SUPPORTED_RATES = (16000, 22050, 24000, 32000, 44100, 48000)


def freeze_policy(sources):
    return {'version': PROFILE, 'selection': 'highest_verified_mp3_stream_bitrate',
            'source_bytes': sum(item['size'] for item in sources),
            'supported_rates': list(SUPPORTED_RATES)}


def choose_encoding(profiles):
    if not profiles:
        raise ValueError('Verified source audio profile evidence is missing')
    rates = {int(profile[1]) for profile in profiles}
    channels = {profile[2] for profile in profiles}
    if len(rates)>1:
        raise ValueError('These audio files use different sample rates. This book needs an encoding review before it can be joined.')
    if not rates.issubset(SUPPORTED_RATES):
        raise ValueError('Selected source sample rates differ or are unsupported; an encoding decision is needed before retrying.')
    if len(channels) > 1:
        raise ValueError('These audio files mix mono and stereo recordings. This book needs an encoding review before it can be joined.')
    if not channels.issubset({1, 2}):
        raise ValueError('This audio recording has more than two channels. This book needs an encoding review before conversion.')
    if any(profile[0] != 'mp3' for profile in profiles):
        raise ValueError('Source-matched AAC selection currently supports MP3 recordings; this source format needs an encoding review.')
    bitrates = []
    for profile in profiles:
        value = profile[3]
        if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isdigit() or not 8000 <= int(value) <= 320000:
            raise ValueError('The app cannot determine suitable audio settings from these source files. This book needs an encoding review before conversion.')
        bitrates.append(int(value))
    rate = next(iter(rates)); channel = next(iter(channels)); target = max(bitrates)
    # Fail rather than let AAC silently clamp a source target above frame capacity.
    if target > 6 * rate * channel:
        raise ValueError('The verified source bitrate exceeds this AAC profile capacity; an encoding decision is needed before retrying.')
    return {'bitrate': target, 'channels': channel, 'sample_rate': rate,
            'source_bitrates': bitrates, 'selection': 'highest_verified_mp3_stream_bitrate'}


AUTOMATIC_PROFILE = 'aac-normalized-or-m4b-copy-quicktime-v4'
AUTOMATIC_RATES = (16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000)
LOSSLESS_CODECS = {'flac', 'alac', 'wavpack', 'pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_f32le', 'pcm_f64le'}
LOSSY_CODECS = {'mp3', 'aac', 'vorbis', 'opus', 'wmav1', 'wmav2', 'wmapro'}


def freeze_automatic_policy(sources):
    return {'version': AUTOMATIC_PROFILE, 'selection': 'preserve_m4b_or_normalize_complete_sources',
            'source_bytes': sum(item['size'] for item in sources),
            'supported_rates': list(AUTOMATIC_RATES)}


def choose_automatic_encoding(profiles, single_m4b=False):
    if not profiles:
        raise ValueError('Verified source audio profile evidence is missing')
    if single_m4b and len(profiles)==1 and profiles[0][0] in ('aac','alac'):
        codec,rate,channel,bitrate=profiles[0][:4]
        layout=profiles[0][4] if len(profiles[0])>4 else None
        known={'mono':1,'stereo':2,'2.1':3,'3.0':3,'quad':4,'4.0':4,'5.0':5,'5.0(side)':5,'5.1':6,'5.1(side)':6,'6.1':7,'7.1':8,'7.1(wide)':8}
        if type(channel) is not int or channel<1 or channel>8 or (channel>2 and known.get(layout)!=channel):
            raise ValueError('Existing M4B multichannel layout cannot be verified for exact preservation')
        if not str(rate).isdigit() or not 8000<=int(rate)<=192000:
            raise ValueError('Existing M4B sample rate cannot be verified')
        return {'mode':'copy','codec':codec,'sample_rate':int(rate),'channels':channel,'channel_layout':layout,
                'bitrate':bitrate,'source_bitrates':[bitrate],'selection':'existing_m4b_audio_stream_copy'}
    rates = []; channels = []; bitrates = []
    for profile in profiles:
        codec, rate, channel, bitrate = profile[:4]
        if isinstance(rate, bool) or not str(rate).isdigit() or not 8000 <= int(rate) <= 96000:
            raise ValueError('Source sample rate cannot be normalized safely')
        if type(channel) is not int or channel not in (1, 2):
            raise ValueError('Multichannel audio requires a verified channel-layout preservation plan')
        if codec not in LOSSLESS_CODECS | LOSSY_CODECS:
            raise ValueError('Source codec has no approved normalization policy')
        rates.append(int(rate)); channels.append(channel)
        if bitrate is not None and not isinstance(bitrate, bool) and str(bitrate).isdigit() and 8000 <= int(bitrate) <= 2000000:
            target = int(bitrate)
        elif codec in LOSSLESS_CODECS:
            target = 128000 * channel
        elif bitrate in (None, '', 'N/A'):
            target = 96000 * channel
        else:
            raise ValueError('Source bitrate evidence is invalid')
        # Lossless PCM bitrate is not a meaningful AAC target.
        bitrates.append(128000 * channel if codec in LOSSLESS_CODECS else target)
    rate = next((value for value in AUTOMATIC_RATES if value >= max(rates)), None)
    channel = max(channels)
    if single_m4b and len(profiles) == 1 and profiles[0][0] in ('aac', 'alac'):
        return {'mode': 'copy', 'codec': profiles[0][0], 'sample_rate': rates[0], 'channels': channel,
                'bitrate': bitrates[0], 'source_bitrates': bitrates, 'selection': 'existing_m4b_audio_stream_copy'}
    target = max(value * channel // source_channel for value,source_channel in zip(bitrates,channels))
    if rate is None or target > 6 * rate * channel:
        raise ValueError('AAC capacity cannot preserve the selected source target safely')
    return {'mode': 'normalize', 'codec': 'aac', 'bitrate': target, 'channels': channel,
            'sample_rate': rate, 'source_bitrates': bitrates,
            'selection': 'complete_sources_pcm_normalization_no_downmix'}
