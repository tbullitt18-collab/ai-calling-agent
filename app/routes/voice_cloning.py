from flask import Blueprint, request, jsonify
import logging
import os
from app.services.elevenlabs_service.voice_cloning import VoiceCloningService
from app.utils.audio_utils import AudioValidator
from app.models.voice_profile import VoiceProfile

logger = logging.getLogger(__name__)
cloning_bp = Blueprint('cloning', __name__)
cloning_service = VoiceCloningService()
voice_profile_model = VoiceProfile()


@cloning_bp.route('/', methods=['GET'])
def list_voices():
    """List all available voices (API + Local Profiles)."""
    import asyncio
    merged_voices = []
    seen_ids = set()
    
    # 1. Fetch from Local MongoDB Profiles (High priority)
    try:
        local_profiles = voice_profile_model.list_user_voices()
        logger.info(f"Retrieved {len(local_profiles)} local voice profiles.")
        for p in local_profiles:
            voice_id = p.get('voice_id')
            if voice_id and voice_id not in seen_ids:
                merged_voices.append({
                    "voice_id": voice_id,
                    "name": p.get('name', 'Cloned Voice'),
                    "source": "local",
                    "status": p.get('status', 'active')
                })
                seen_ids.add(voice_id)
    except Exception as e:
        logger.error(f"Error fetching local profiles: {e}")

    # 2. Fetch from ElevenLabs API (Fallback)
    try:
        api_voices = asyncio.run(cloning_service.list_voices())
        logger.info(f"Retrieved {len(api_voices)} voices from ElevenLabs API.")
        for v in api_voices:
            voice_id = v.get('voice_id')
            if voice_id not in seen_ids:
                merged_voices.append({
                    "voice_id": voice_id,
                    "name": v.get('name'),
                    "source": "elevenlabs",
                    "status": "active"
                })
                seen_ids.add(voice_id)
    except Exception as e:
        logger.error(f"Error fetching ElevenLabs voices: {e}")
        # We don't fail the whole request if local voices were found

    return jsonify(merged_voices)




@cloning_bp.route('/clone', methods=['POST'])
def clone_voice():
    """
    Handle voice sample uploads and initiate cloning.
    Expects multi-part form data with 'name' and 'files'.
    """
    import asyncio
    if 'files' not in request.files:
        return jsonify({"error": "No audio files provided"}), 400
        
    name = request.form.get('name', 'Custom Voice')
    uploaded_files = request.files.getlist('files')
    
    # Temporary save for processing (as required by current ElevenLabs PVC flow)
    temp_paths = []
    os.makedirs('temp_uploads', exist_ok=True)
    
    try:
        for f in uploaded_files:
            path = os.path.join('temp_uploads', f.filename)
            f.save(path)
            
            # AUDIO VALIDATION (New in v2.0)
            if f.filename.lower().endswith('.wav'):
                is_valid, error = AudioValidator.validate_wav(path)
                if not is_valid:
                    logger.warning(f"Audio validation failed for {f.filename}: {error}")
                    return jsonify({"error": f"Invalid audio {f.filename}: {error}"}), 400
            
            temp_paths.append(path)
            
        # Initiate cloning with ElevenLabs
        voice_id = asyncio.run(cloning_service.clone_voice(name, temp_paths))
        
        # PERSISTENCE (New in v2.0)
        profile_id = voice_profile_model.create_profile(voice_id, name)
        
        return jsonify({
            "status": "success",
            "voice_id": voice_id,
            "profile_id": profile_id,
            "message": "Cloning process initiated and profile created."
        })

    except Exception as e:
        logger.error(f"Cloning error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Cleanup temp files after handoff to ElevenLabs
        for p in temp_paths:
            if os.path.exists(p): os.remove(p)

@cloning_bp.route('/link', methods=['POST'])
def link_voice():
    """Manually link an existing ElevenLabs voice ID."""
    data = request.get_json()
    name = data.get('name')
    voice_id = data.get('voice_id')
    
    if not name or not voice_id:
        return jsonify({"error": "Missing name or voice_id"}), 400
        
    try:
        profile_id = voice_profile_model.create_profile(voice_id, name)
        return jsonify({
            "status": "success",
            "voice_id": voice_id,
            "profile_id": profile_id,
            "message": "Existing voice linked successfully."
        })
    except Exception as e:
        logger.error(f"Linking error: {e}")
        return jsonify({"error": str(e)}), 500


@cloning_bp.route('/<voice_id>', methods=['DELETE'])

async def delete_voice(voice_id: str):
    """Delete a custom voice."""
    success = await cloning_service.delete_voice(voice_id)
    return jsonify({"success": success})
