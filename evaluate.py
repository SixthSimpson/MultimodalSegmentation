import json
import sys


def label_at(t: float, segments: list) -> str:
    """Return the label active at time t."""
    for seg in segments:
        if seg['start'] <= t < seg['end']:
            return seg['label']
    return 'video_content'


def per_second_accuracy(pred_segments, truth_segments, duration):
    """For each second, check if predicted label matches truth."""
    correct = 0
    total = int(duration)
    
    for sec in range(total):
        if label_at(sec, pred_segments) == label_at(sec, truth_segments):
            correct += 1
    
    return correct / total if total > 0 else 0


def ad_detection_metrics(pred_segments, truth_segments):
    """Did we detect each true ad (any overlap counts)?"""
    true_ads = [s for s in truth_segments if s['label'] == 'advertisement']
    pred_ads = [s for s in pred_segments if s['label'] == 'advertisement']
    
    detected = 0
    for true_ad in true_ads:
        for pred_ad in pred_ads:
            if pred_ad['start'] < true_ad['end'] and pred_ad['end'] > true_ad['start']:
                detected += 1
                break

    recall = detected / len(true_ads) if true_ads else 0

    correctly_predicted = 0
    for pred_ad in pred_ads:
        for true_ad in true_ads:
            if pred_ad['start'] < true_ad['end'] and pred_ad['end'] > true_ad['start']:
                correctly_predicted += 1
                break
    
    precision = correctly_predicted / len(pred_ads) if pred_ads else 0
    
    return {
        'true_ads': len(true_ads),
        'predicted_ads': len(pred_ads),
        'detected_ads': detected,
        'recall': recall,
        'precision': precision,
    }


def boundary_accuracy(pred_segments, truth_segments):
    """How close are predicted ad boundaries to true ad boundaries?"""
    true_boundaries = []
    for s in truth_segments:
        if s['label'] == 'advertisement':
            true_boundaries.extend([s['start'], s['end']])
    
    pred_boundaries = []
    for s in pred_segments:
        if s['label'] == 'advertisement':
            pred_boundaries.extend([s['start'], s['end']])
    
    if not true_boundaries or not pred_boundaries:
        return None
    
    errors = []
    for tb in true_boundaries:
        closest = min(pred_boundaries, key=lambda pb: abs(pb - tb))
        errors.append(abs(closest - tb))
    
    return {
        'avg_boundary_error_sec': sum(errors) / len(errors),
        'max_boundary_error_sec': max(errors),
    }


def evaluate(pred_path: str, truth_path: str):
    with open(pred_path) as f:
        pred = json.load(f)
    with open(truth_path) as f:
        truth = json.load(f)
    
    duration = truth['duration_sec']
    
    print(f"\n{'='*60}")
    print(f"Evaluating: {pred.get('video_id', '?')}")
    print(f"Method:     {pred.get('method', '?')}")
    print(f"{'='*60}")
    
    acc = per_second_accuracy(pred['segments'], truth['segments'], duration)
    ad_metrics = ad_detection_metrics(pred['segments'], truth['segments'])
    boundaries = boundary_accuracy(pred['segments'], truth['segments'])
    
    print(f"\nPer-second accuracy: {acc:.1%}")
    print(f"\nAd detection:")
    print(f"  True ads:      {ad_metrics['true_ads']}")
    print(f"  Predicted ads: {ad_metrics['predicted_ads']}")
    print(f"  Detected:      {ad_metrics['detected_ads']}/{ad_metrics['true_ads']}")
    print(f"  Recall:        {ad_metrics['recall']:.1%}")
    print(f"  Precision:     {ad_metrics['precision']:.1%}")
    
    if boundaries:
        print(f"\nBoundary accuracy:")
        print(f"  Avg error: {boundaries['avg_boundary_error_sec']:.1f}s")
        print(f"  Max error: {boundaries['max_boundary_error_sec']:.1f}s")
    print()


if __name__ == '__main__':
    pred_path = sys.argv[1] if len(sys.argv) > 1 else 'data/predictions/test_001_baseline.json'
    truth_path = sys.argv[2] if len(sys.argv) > 2 else 'data/source_of_truth_flat/test_001.json'
    evaluate(pred_path, truth_path)