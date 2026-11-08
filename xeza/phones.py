import phonenumbers
from phonenumbers import carrier, geocoder, timezone

async def profile_phone(phone: str):
    results = []
    try:
        parsed = phonenumbers.parse(phone)
        if not phonenumbers.is_valid_number(parsed):
            return [{"kind": "Error", "value": "Invalid phone number format", "score": 0, "method": "Parser"}]
        
        country = geocoder.description_for_number(parsed, "en")
        isp = carrier.name_for_number(parsed, "en")
        tz = ", ".join(timezone.time_zones_for_number(parsed))
        num_type = phonenumbers.number_type(parsed)
        
        results.append({"kind": "Phone Geo", "value": f"Country/Region: {country or 'Unknown'}", "score": 3, "method": "GeoLocator"})
        results.append({"kind": "Carrier Info", "value": f"Telecom Carrier: {isp or 'Unknown / VoIP'}", "score": 4, "method": "HLR Lookup"})
        results.append({"kind": "Timezone", "value": f"Associated Timezones: {tz}", "score": 2, "method": "TZ Analysis"})
        
        clean_num = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164).replace("+", "")
        results.append({
            "kind": "WhatsApp Direct",
            "value": f"Open WhatsApp chat for +{clean_num}",
            "score": 6,
            "method": "API Vector",
            "url": f"https://wa.me/{clean_num}"
        })
        results.append({
            "kind": "Telegram Direct",
            "value": f"Open Telegram link for +{clean_num}",
            "score": 6,
            "method": "API Vector",
            "url": f"https://t.me/+{clean_num}"
        })
    except Exception as e:
        results.append({"kind": "Error", "value": f"Phone parse failure: {str(e)}", "score": 0, "method": "Exception"})
    return results