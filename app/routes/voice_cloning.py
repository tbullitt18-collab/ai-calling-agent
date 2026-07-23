from flask import Blueprint, request, jsonify, session
import logging
import os
import json
import httpx
from app.utils.audio_utils import AudioValidator
from app.models.voice_profile import VoiceProfile
from app.config import ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)
cloning_bp = Blueprint('cloning', __name__)
voice_profile_model = VoiceProfile()


@cloning_bp.route('/', methods=['GET'])
def list_voices():
    """List available voices for selection."""
    voices = [
        {"voice_id": "en-US-Studio-O", "name": "Google Studio (Female - Conversational)", "source": "system", "status": "active"},
        {"voice_id": "en-US-Studio-Q", "name": "Google Studio (Male - Conversational)", "source": "system", "status": "active"},
        {"voice_id": "en-US-Journey-F", "name": "Google Journey (Female - Expressive)", "source": "system", "status": "active"},
        {"voice_id": "en-US-Journey-O", "name": "Google Journey (Male - Expressive)", "source": "system", "status": "active"},
        {"voice_id": "en-US-Casual-K", "name": "Google Casual (Male - Casual)", "source": "system", "status": "active"},
    ]
    
    # Also fetch THIS user's custom voices from MongoDB (not all users)
    try:
        user_id = session.get('username', 'default')
        user_voices = voice_profile_model.list_user_voices(user_id)
        for p in user_voices:
            voices.append({
                "voice_id": p.get("voice_id"),
                "name": p.get("name"),
                "source": "local",
                "status": "active"
            })
    except Exception as e:
        logger.warning(f"Could not load custom profiles from DB: {e}")
        
    return jsonify(voices)


@cloning_bp.route('/clone', methods=['POST'])
def clone_voice():
    """
    ElevenLabs Instant Voice Clone.
    Expects multi-part form data with 'name' and 'files'.
    """
    if 'files' not in request.files:
        return jsonify({"error": "No audio files provided"}), 400
        
    name = request.form.get('name', 'Custom Voice')
    uploaded_files = request.files.getlist('files')
    
    temp_paths = []
    os.makedirs('temp_uploads', exist_ok=True)
    
    try:
        for f in uploaded_files:
            path = os.path.join('temp_uploads', f.filename)
            f.save(path)
            
            # AUDIO VALIDATION (Required for Custom Voice)
            if f.filename.lower().endswith('.wav'):
                is_valid, error = AudioValidator.validate_wav(path)
                if not is_valid:
                    logger.warning(f"Audio validation failed for {f.filename}: {error}")
                    return jsonify({"error": f"Invalid audio {f.filename}: {error}"}), 400
            
            temp_paths.append(path)
            
        # Call ElevenLabs Instant Voice Cloning API
        logger.info(f"Submitting {len(temp_paths)} audio samples to ElevenLabs for voice cloning...")
        
        file_handles = [open(p, "rb") for p in temp_paths]
        try:
            files_payload = [("files", (os.path.basename(p), fh)) for p, fh in zip(temp_paths, file_handles)]
            data_payload = {
                "name": name,
                "labels": json.dumps({"category": "cloned", "app": "raincheck"}),
            }
            
            response = httpx.post(
                "https://api.elevenlabs.io/v1/voices/add",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                data=data_payload,
                files=files_payload,
                timeout=60.0,
            )
            response.raise_for_status()
        finally:
            for fh in file_handles:
                fh.close()
        
        voice_id = response.json()["voice_id"]
        
        # PERSISTENCE
        user_id = session.get('username', 'default')
        profile_id = voice_profile_model.create_profile(voice_id, name, user_id=user_id)
        logger.info(f"ElevenLabs voice cloned: {voice_id} ({name})")
        
        return jsonify({
            "status": "success",
            "voice_id": voice_id,
            "profile_id": profile_id,
            "message": "Voice cloning complete and profile created."
        })

    except httpx.HTTPStatusError as e:
        logger.error(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"ElevenLabs API error: {e.response.text}"}), 502

    except Exception as e:
        logger.error(f"Voice cloning error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Cleanup temp files
        for p in temp_paths:
            try:
                if os.path.exists(p): os.remove(p)
            except OSError:
                pass


@cloning_bp.route('/<voice_id>', methods=['PUT'])
def update_voice(voice_id: str):
    """Update a custom voice profile's name."""
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    characteristics = data.get('characteristics')

    updates = {}
    if name:
        updates['name'] = name
    if characteristics:
        updates['characteristics'] = characteristics

    if not updates:
        return jsonify({"error": "No fields to update"}), 400

    try:
        success = voice_profile_model.update_profile(voice_id, updates)
        if success:
            return jsonify({"status": "success", "message": "Voice profile updated."})
        else:
            return jsonify({"error": "Voice profile not found or unchanged"}), 404
    except Exception as e:
        logger.error(f"Update voice error: {e}")
        return jsonify({"error": str(e)}), 500


@cloning_bp.route('/<voice_id>', methods=['DELETE'])
def delete_voice(voice_id: str):
    """Delete a custom voice profile from MongoDB and ElevenLabs."""
    try:
        success = voice_profile_model.delete_profile(voice_id)
        
        # Also delete from ElevenLabs (best-effort)
        try:
            resp = httpx.delete(
                f"https://api.elevenlabs.io/v1/voices/{voice_id}",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                timeout=15.0,
            )
            resp.raise_for_status()
            logger.info(f"Deleted voice {voice_id} from ElevenLabs")
        except Exception as el_err:
            logger.warning(f"Failed to delete voice {voice_id} from ElevenLabs: {el_err}")
        
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Delete voice error: {e}")
        return jsonify({"error": str(e)}), 500
