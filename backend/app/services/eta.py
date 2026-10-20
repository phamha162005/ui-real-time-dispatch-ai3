from datetime import datetime, timedelta

def dt(s):
    return datetime.fromisoformat(s) if isinstance(s,str) else s

def evaluate(trip, now):
    complete = trip["status"] == "hoan_thanh"
    start = max(now, dt(trip["start_at"]))
    eta = dt(trip["completed_at"]) if complete and trip.get("completed_at") else start + timedelta(minutes=trip["remaining_minutes"])
    if trip.get("eta_manual") and not complete:
        eta = max(eta,dt(trip["eta_manual"]))
    cutoff=dt(trip["cutoff"])
    slack=(cutoff-eta).total_seconds()/60
    left=(cutoff-now).total_seconds()/60
    if complete:
        risk = "cao" if slack<0 else "thap"
        reason = "Đã hoàn thành sau cut-off" if slack<0 else "Đã hoàn thành đúng hạn"
    elif left<0:
        risk,reason="cao","Đã quá cut-off, chuyến chưa hoàn thành"
    elif slack<0:
        risk,reason="cao",f"ETA vượt cut-off {abs(slack):.0f} phút"
    elif slack<30:
        risk,reason="trung_binh",f"Chỉ còn {slack:.0f} phút dự phòng (ngưỡng 30 phút)"
    else:
        risk,reason="thap",f"Dự phòng {slack:.0f} phút trước cut-off"
    return {**trip,"eta":eta.isoformat(),"buffer_minutes":round(slack,1),"cutoff_remaining_minutes":round(left,1),"risk":risk,"risk_reason":reason,"utilization":round(trip["load"]/trip["capacity"]*100,1)}

def progress(trip, old, now):
    if trip["status"] != "dang_chay": return
    effective=max(old,dt(trip["start_at"]))
    elapsed=max(0,(now-effective).total_seconds()/60)
    prior=trip["remaining_minutes"]
    trip["remaining_minutes"]=max(0,prior-elapsed)
    if trip["remaining_minutes"]<=0 and elapsed>0:
        arrival=effective+timedelta(minutes=prior)
        if trip.get("eta_manual"): arrival=max(arrival,dt(trip["eta_manual"]))
        if now>=arrival:
            trip["status"]="hoan_thanh"
            trip["completed_at"]=arrival.isoformat()
