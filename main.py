
from ml.local_training import train_local_model


def main():
    results = []

    for hospital_id in range(1, 4):
        result = train_local_model(
            hospital_id=hospital_id,
            round_number=1
        )
        results.append(result)

    print("\n" + "=" * 55)
    print("FEDHEALTH: LOCAL TRAINING SUMMARY")
    print("=" * 55)

    for result in results:
        print(
            f"Hospital {result['hospital_id']} | "
            f"Samples: {result['sample_count']} | "
            f"Accuracy: {result['accuracy']:.4f} | "
            f"Recall: {result['recall']:.4f} | "
            f"F1: {result['f1_score']:.4f}"
        )

    print("\nAll three hospitals completed local training.")


if __name__ == "__main__":
    main()
