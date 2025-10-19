AWS Chatbot Slack Monitor Project

This project template is based on the [https://github.com/danjamk/pycharm-claude-devcontainer](https://github.com/danjamk/pycharm-claude-devcontainer) template, but other than using the devcontainer approach for development, has no relationships.

The purpose of this project is to create an AWS stack using AWS CDK code written in python that integrates AWS budget and other monitoring into one or more slack channels. This will be a public repo to share with others so they can do the same \- and for me to use on different client projects as an accelerator. 

The motivation is that it is very easy to make a mistake early and not notice runaway costs. Slack is a place teams work and collaborate together, and I would like to integrate notifications into this.

AWS has a Chatbot service that really enhances this capability, allowing integration of CloudWatch, budget alarms, SNS notifications into slack.  

Reminder that we are operating in a pycharm dev container with limited access.  

Initial tasks

1. Web research on the proper approach for building out the stack for this project  
2. Review my specs below and then ask clarifying questions about the implementation for this project.  
3. Create a [claude.md](http://claude.md) file for this project with the context it will need.  The current version is for the dev container project.  
4. The existing project is for the dev container, so we want to refactor it to be for this project.  Move and modify the existing [readme.md](http://readme.md) file to the .devcontainer folder \- so it remains good documentation for anyone referencing this project \- with the source repo that it came from.   
5. Recreate a new project [readme.md](http://readme.md) file that is relevant to this project  
6. Create a [project-plan.md](http://project-plan.md) file in the doc folder that is a detailed implementation plan for this project.  It will ground our work.   We will update it with status as we proceed \- and make any updates if we adjust our approach.  
7. We need to create an AWS deployment user per the dev container instructions with the proper permissions needed for this stack.  So once you understand this you will update the scripts/[aws-permissions-config.sh](http://aws-permissions-config.sh) file to enable these permissions. I will then run the script outside this container and complete the setup for AWS access.  
8. Github interactions.  This project only has read only access to this project.  When I ask to commit, create a detailed commit message and create or modify the [GIT-COMMIT-MSG.md](http://GIT-COMMIT-MSG.md) file.  Then provide the commit command that will use this as the commit message.  When I ask to the a PR or pull request, do the same but with [GIT-PULLREUQEST-MSG.md](http://GIT-PULLREUQEST-MSG.md) file.     

Project requirements

* Again, this will use [https://aws.amazon.com/chatbot/](https://aws.amazon.com/chatbot/) as the core feature  
* The primary use case is to publish notifications about cost and resource usage to a slack channel for the team.  So we need to create the stack needed for that.  
* We should create a basic configuration file that allows this project to be a useful template.  This configuration should only be safe information.  We will use .env to define any secrets needed for the project.   
* Secrets that the stack needs to operate will be deployed to AWS secret store during the deployment process.  Along with any configuration references (for example slack integration details).  
* Slack Channels \- in the past, I have used two slack channels. One for critical, must react to events. This one is not noisy.  Any message is critical.   And on for observing the heartbeat of the system.. Messages that indicate events are occurring properly.  Maybe trivial errors or warnings, etc.  This can be noisy. I would like to use this approach here of we can.    
* For AWS cost management \- here are my thoughts on requirements (but suggest improvements if you feel it can be better).  I like to monitor daily.  So we want a daily budget and notifications relative to this.  We will also want a monthly budget and tracking to that.  The configuration template should allow for setting these up. I mentioned two types of notification channels.  I think we can send daily spend notifications to the heartbeat channel and warnings when we get close to budget limits (80%), while we send budget overrides to the critical channel.  Budgets should be configurable  
* I would like it to be easy to tweak budgets and run a “make deploy” script to update them as needed  
* I like to use make commands \- “make deploy”, “make destroy”, etc.  \- and these should be safe and easy to run to make updates as needed. Also a “make validate” \- since this is a notifications system, maybe we have a make command to also test the notifications path to slack on both channels.  
* We should provide instructions on setting up slack integration on the slack side   
* We should also create a simple cloudwatch dashboard for monitoring costs/budget  
* Budgets alerts should also include an optional list of emails to send notifications to.  
* I would like to be able to integrate other notifications into slack here.  I’m not sure yet, but for infrastructure where we might care about other alerts critical to the stacks (ECS server down, EMR task failed, etc.).  It might be nothing more than providing instructions to be used in other stacks on how to integrate with this channel.  That is probably the best approach.    
* I want to make best use of the AWS chabot service.  If I understand this, it will not only help in integrating notifications, but also allow the user in slack to ask messages and get help troubleshooting and interrogating the system.  I want to make sure we are creating an integration that accomplishes that well.  
* We want excellent message formatting in slack.

  

