def report(trips):
    active=[t for t in trips if t['status']!='hoan_thanh']
    done=[t for t in trips if t['status']=='hoan_thanh']
    at_risk=[t for t in active if t['risk']!='thap']
    cost=sum(t['cost'] for t in trips)
    avoided=sum(t.get('estimated_saving',0) for t in trips)
    return {'total_trips':len(trips),'active_trips':len(active),'completed_trips':len(done),'at_risk':len(at_risk),'risk_rate':round(len(at_risk)/len(active)*100,1) if active else 0,'on_time_rate':round(sum(t['buffer_minutes']>=0 for t in done)/len(done)*100,1) if done else None,'total_cost':cost,'estimated_saving':round(avoided),'average_cost':round(cost/len(trips)) if trips else 0,'utilization':round(sum(t['utilization'] for t in active)/len(active),1) if active else 0,'risk_counts':{k:sum(t['risk']==k for t in active) for k in ['thap','trung_binh','cao']},'costs':[{'code':t['code'],'cost':t['cost']} for t in trips],'note':'Chỉ số mô tả tập chuyến hiện tại, không phải hiệu quả thực tế kỳ trước – kỳ sau. Khoản tiết kiệm là ước tính theo phương án, chưa phải chi phí đã tiết kiệm.'}
