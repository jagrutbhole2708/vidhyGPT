# AWS S3 & IAM Setup Guide for VidhyaGPT

This guide walks you through setting up an Amazon S3 bucket to store rendered videos and creating an IAM user with the precise permissions needed by the Python service.

---

## Part 1: Creating the S3 Bucket

1. Log into your AWS Management Console.
2. Search for **S3** and click **Create bucket**.

### General Configuration
- **Bucket name**: Choose a globally unique name (e.g., `vidyagpt-client-videos-2026`).
- **AWS Region**: Select the region closest to your users or your Render server (e.g., `us-east-1` for US East). Leave everything else as default.

### Object Ownership
- Select **ACLs disabled (recommended)**.

### Block Public Access settings for this bucket
By default, AWS blocks all public access. Since your Next.js app needs to stream these videos to users, the objects must be publicly readable.
- **Uncheck** the box that says **Block *all* public access**.
- Check the acknowledgment box that appears below it ("I acknowledge that the current settings might result in this bucket and the objects within becoming public").

### Bucket Versioning & Default Encryption
- **Bucket Versioning**: Disable (to save costs on old video renders).
- **Default encryption**: Leave as **Server-side encryption with Amazon S3 managed keys (SSE-S3)**.

Click **Create bucket** at the very bottom.

---

## Part 2: Configuring Bucket Permissions

Once the bucket is created, click on its name to open it, then go to the **Permissions** tab.

### 1. Bucket Policy (Make videos publicly readable)
Scroll down to **Bucket policy** and click **Edit**.
Paste the following JSON block, making sure to replace `YOUR-BUCKET-NAME` with the actual name of your bucket:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
        }
    ]
}
```
*Click **Save changes**.*

### 2. CORS (Cross-Origin Resource Sharing)
Scroll down to **Cross-origin resource sharing (CORS)** and click **Edit**.
Since your frontend will request these video files directly from S3, you need to allow your domain to access them. Paste this JSON block:

```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "GET",
            "HEAD"
        ],
        "AllowedOrigins": [
            "*"
        ],
        "ExposeHeaders": [
            "ETag"
        ],
        "MaxAgeSeconds": 3000
    }
]
```
*(Note: `AllowedOrigins: ["*"]` is the easiest setup. Once you are in production, you can replace `"*"` with your exact Vercel domains like `["https://vidyagpt.com"]` for extra security).*
*Click **Save changes**.*

---

## Part 3: Creating the IAM User for the Python Service

Your Python service needs permission to upload files to this new bucket.

1. In the AWS Management Console search bar, type **IAM** and select it.
2. On the left sidebar, click **Users**, then click **Create user** on the right.
3. **User details**: Name the user something descriptive (e.g., `vidyagpt-s3-uploader`). Click **Next**.
4. **Set permissions**: 
   - Select **Attach policies directly**.
   - In the search bar below it, type `AmazonS3FullAccess`.
   - Check the box next to **AmazonS3FullAccess**.
   *(If you want to be extremely secure, you can create an inline policy that only grants `s3:PutObject` to this specific bucket, but `AmazonS3FullAccess` is standard for a dedicated service account).*
   - Click **Next**, then **Create user**.

### Generating Access Keys
1. Once the user is created, click on the user's name (`vidyagpt-s3-uploader`) from the Users list.
2. Go to the **Security credentials** tab.
3. Scroll down to **Access keys** and click **Create access key**.
4. Select **Application running outside AWS**.
5. Click **Next**, then click **Create access key**.

**🚨 IMPORTANT:** Copy the **Access Key ID** and **Secret Access Key** immediately. You will not be able to see the Secret Access Key again after you close this page.

---

## Part 4: Updating Environment Variables

Take those keys and update your `.env` file (and your Render Environment Variables):

```env
AWS_ACCESS_KEY_ID="<The Access Key ID you just generated>"
AWS_SECRET_ACCESS_KEY="<The Secret Access Key you just generated>"
AWS_DEFAULT_REGION="<The region you selected in Part 1, e.g., us-east-1>"
AWS_S3_BUCKET="<The exact name of the bucket you created in Part 1>"
```

You're all set! Your Python service can now securely upload to S3, and your Next.js app can securely display the videos to your users.
