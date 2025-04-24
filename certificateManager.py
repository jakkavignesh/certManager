import boto3
import os
import pandas as pd
from datetime import datetime, timedelta, timezone

aws_profiles = [
    'investor-mangement-services'
]

aws_regions = [
    'us-east-1',
    'us-west-2'
]

expired_certificates_details = []
expiring_certificates_details = []

def extract_parts(domain):
    parts = domain.split('.')
    
    if parts[1] == "imsdev":
        return parts[0]
    elif parts[0] == 'investors':
        return parts[1]
    else:
        return domain

def sendNotification(message_list):
    if not message_list:
        print("No expiring certificates to notify.")
        return

    message_body = "These are the SSL certificates which are going to expire in next 30 days, please verify and confirm the investors who are active."
    message_body += "\n\nExpiring Certificates:\n\n"
    
    for item in message_list:
        domain = item.split(',')[0].split(': ')[1]
        certificate_name = extract_parts(domain)
        expiration_date = item.split(',')[1].split(': ')[1]
        message_body += f"- Domain: {domain} | Expiration Date: {expiration_date} | Certificate Name: {certificate_name}\n"

    snsClient = boto3.client('sns', region_name='us-west-2')
    snsClient.publish(
        TopicArn='arn:aws:sns:us-west-2:359459309488:CertExpirationNotifications-Test',
        Message=message_body,
        Subject="SSL certificates expiration report"
    )

    print("Notification sent successfully")

def get_certificate_manager_details(arns_list, profile, region):
    for arn in arns_list:
        certificate_details = []
        try: 
            certificate_manager_client = boto3.client('acm', region_name = region)
            certificates = certificate_manager_client.describe_certificate(CertificateArn = arn)
            not_after = certificates['Certificate']['NotAfter'].replace(tzinfo=timezone.utc)
            formatted_not_after = not_after.strftime('%Y-%m-%d')
            domain_name = certificates['Certificate']['DomainName']
            details = {
                'Domain name': domain_name,
                'Expiration Date': formatted_not_after
            }
            certificate_details.append(details)
            expired_certificates_details.extend(certificate_details)
            if not_after <= datetime.now(timezone.utc) + timedelta(days=30):
                expiring_certificates_details.append(f"Domain: {domain_name}, Expiration Date: {formatted_not_after}")

        except Exception as error:
            print(f'Problem in : {profile} Error : {error}')
            continue

def get_certificates_list():
    for profile in aws_profiles:
        for region in aws_regions:
            expired_certificates_arns = []
            try:
                certificate_manager_client = boto3.client('acm', region_name = region)
                expired_certificates = certificate_manager_client.list_certificates(CertificateStatuses = ['ISSUED',])
                for certificate in expired_certificates['CertificateSummaryList']:
                    expired_certificates_arns.append(certificate['CertificateArn'])
                get_certificate_manager_details(expired_certificates_arns, profile, region)
            except Exception as error:
                print(f'Problem in : {profile} Error : {error}')
                continue
            print("Done " + profile)
    
    sendNotification(expiring_certificates_details)
def main():
    get_certificates_list()

if __name__ == '__main__':
    main()